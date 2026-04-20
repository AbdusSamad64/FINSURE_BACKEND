import asyncio
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Transaction, Category
from app.categorization.config import config
from app.categorization.llm_client import llm_categorize_batch

logger = logging.getLogger(__name__)

async def categorization_worker():
    """
    Background worker that polls for transactions with NULL categID
    and categorizes them using LLM in batches.
    """
    logger.info("Starting categorization worker...")
    
    while True:
        try:
            # We use a new session for each poll cycle
            db: Session = SessionLocal()
            try:
                # 1. Fetch transactions needing categorization
                # Limit to 5 batches worth of work per cycle to keep it responsive
                unlabeled = (
                    db.query(Transaction)
                    .filter(Transaction.categID == None)
                    .limit(config.batch_size * 5)
                    .all()
                )

                if not unlabeled:
                    logger.debug("No transactions to categorize. Sleeping...")
                    db.close()
                    await asyncio.sleep(config.worker_interval_sec)
                    continue

                msg = f"Picked up {len(unlabeled)} transactions for LLM categorization"
                logger.info(msg)
                print(f"\n[CAT-WORKER] {msg}")


                # 2. Prepare metadata (categories)
                categories = db.query(Category).all()
                cat_list = [c.name for c in categories]
                cat_map = {c.name: c.categID for c in categories}

                # 3. Process in batches
                for i in range(0, len(unlabeled), config.batch_size):
                    batch_rows = unlabeled[i : i + config.batch_size]
                    
                    # Convert to minimal dict for LLM
                    batch_data = []
                    for r in batch_rows:
                        batch_data.append({
                            "trxID": r.trxID,
                            "description": r.trxDetail,
                            "tx_type": "Incoming" if r.trxType.lower() == "credit" else "Outgoing",
                            "amount": r.amount
                        })

                    # 4. Call LLM
                    results = llm_categorize_batch(batch_data, cat_list, cat_map)

                    # 5. Apply results to DB
                    # We map trxID to the object for optimization
                    obj_map = {r.trxID: r for r in batch_rows}
                    for res in results:
                        trx_obj = obj_map.get(res["trxID"])
                        if trx_obj:
                            trx_obj.categID = res["categID"]
                            trx_obj.categorized_by = res["categorized_by"]
                            log_msg = f"Categorized trxID={res['trxID']} as ID={res['categID']} via {res['categorized_by']}"
                            logger.info(log_msg)
                            print(f"[CAT-WORKER] {log_msg}")
                    
                    db.commit()
                    logger.info(f"Committed batch of {len(results)} updates")
                    print(f"[CAT-WORKER] Committed batch of {len(results)} updates\n")


                    # Inter-batch delay to stay under RPM/TPM limits
                    if i + config.batch_size < len(unlabeled):
                        logger.info(f"[categorizer] Sleeping for {config.batch_delay_sec}s between batches...")
                        await asyncio.sleep(config.batch_delay_sec)


            except Exception as e:
                logger.error(f"Error in categorization worker loop: {e}", exc_info=True)
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Critical worker error (Session setup failed?): {e}")

        # Wait for the next cycle
        await asyncio.sleep(config.worker_interval_sec)
