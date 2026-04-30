from app.utils.extraction_helpers import clean_brackets,is_number,is_int_convertible,is_date,is_amount,clean_amount,is_date_of_meezan
import re
def extract_transaction_of_easypaisa(filepath,page_no,total_no_pages, extract_account=False):
    if total_no_pages==0:
        return "No pages to extract transactions"
    if total_no_pages==1:
        skip_lines_from_start=31   #unwanted header
        skip_lines_from_end=8      #unwanted footer
    elif page_no==1:
        skip_lines_from_start=31
        skip_lines_from_end=2
    elif page_no==total_no_pages:
        skip_lines_from_start=25
        skip_lines_from_end=8
    else:
        skip_lines_from_start=25
        skip_lines_from_end=2

    with open(filepath,"r") as file:
        lines = [line.strip() for line in file if line.strip()]  # remove empty lines
    account_number = None
    if extract_account:
        account_number = lines[5]   # extract only once    
    lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]
    
    transactions=[]
    block_size = 24    #pattern of 24 lines are repeating

     # Split lines into initial blocks
    blocks = [lines[i:i + block_size] for i in range(0, len(lines), block_size)]

    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(blocks):
            #added by 10/11
            while True:
                block = blocks[i] 
                if is_number(block[1]) and len(block)==24:
                    break  # if first element is numeric
                if  not is_number(block[1]): # if not numeric 
                    changed = True
                    # merge block[0] and block[1]
                    block[0] = f"{block[0]} {block[1]}".strip()
                    block.pop(1)

                    # if next block exists, move its 0th element here
                    if i + 1 < len(blocks):
                        next_block = blocks[i + 1]
                        if next_block:
                            elements_req=24-len(block)
                            for j in range(elements_req):
                                block.append(next_block.pop(0))

                            # if next block becomes empty, remove it
                            if len(next_block) == 0:
                                blocks.pop(i + 1)
                    
                #add
                if len(block)!=24:
                        if i + 1 < len(blocks):
                            next_block = blocks[i + 1]
                        if next_block:
                            elements_req=24-len(block)
                            for k in range(elements_req):
                                block.append(next_block.pop(0))

                            # if next block becomes empty, remove it
                            if len(next_block) == 0:
                                blocks.pop(i + 1)
            #till            

            i += 1
   
    for block in blocks:
        if len(block) < block_size:
            continue
        dict={}  
        dict['description'] = clean_brackets(block[0])
        dict['opening_balance'] = clean_brackets(block[1])
        dict['incoming'] = clean_brackets(block[2])
        dict['outgoing'] = clean_brackets(block[3])
        dict['closing_balance'] = clean_brackets(block[4])
        dict['date'] = clean_brackets(block[5])
        dict['time'] = clean_brackets(block[6])
        dict['transaction_id'] = clean_brackets(block[18])
        transactions.append(dict)
        dict={}
    return transactions,account_number

# def extract_transaction_of_meezan(filepath,page_no,total_no_pages,extract_account=False):
#     if total_no_pages==0 or total_no_pages==1:
#         return "No pages to extract transactions"
#     else:
#         skip_lines_from_start=29
#         skip_lines_from_end=12
#     account_number = None
    
#     with open(filepath,"r") as file:
#         lines = [line.strip() for line in file if line.strip()]  # remove empty lines
   
#     if (is_int_convertible(lines[8])==True and lines[7]!='MEEZAN KAFALAH ACCOUNT'):  #asaan account statement
#         if extract_account:
#             account_number = lines[8]
#         lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]
#     elif lines[7]=='MEEZAN KAFALAH ACCOUNT':
#         if extract_account:
#             account_number = lines[8]
#         lines = lines[skip_lines_from_start-1:len(lines)-skip_lines_from_end]   
#     else:                                                                             # saving account statement
#         if extract_account:
#             account_number = lines[9]   # extract only once 
#         lines = lines[skip_lines_from_start+1:len(lines)-skip_lines_from_end]   

    
#     transactions=[]
#     block_size = 6    #pattern of 6 lines are repeating

#     #  # Split lines into initial blocks
#     blocks = [lines[i:i + block_size] for i in range(0, len(lines), block_size)]
#     # print(blocks)
#     changed = True
#     while changed:
#         changed = False
#         i = 0
        
#         while i < len(blocks):
#             #added by 10/11
#             # while True:
#             inner_count=0
#             while inner_count<10:
#                 inner_count+=1    
#                 block = blocks[i]
#                 #added for block protection
#                 if len(block)<4:
#                     # print("detected less blocks")
#                     if i + 1 < len(blocks):
#                         next_block=blocks[i+1]
#                         elements_req=6-len(block)
#                         for j in range(elements_req):
#                             block.append(next_block.pop(0))  
#                         # if next block becomes empty, remove it
#                         if len(next_block) == 0:
#                             blocks.pop(i + 1)    
#                 #till here      
#                 if is_number(block[3]) and len(block)==6:
#                     break  # if first element is numeric
#                 if  not is_number(block[3]): # if not numeric 
#                     changed = True
#                     # merge block[2] and block[3]
#                     block[2] = f"{block[2]} {block[3]}".strip()
#                     block.pop(3)

#                     # if next block exists, move its 0th element here
#                     if i + 1 < len(blocks):
#                         next_block = blocks[i + 1]
#                         if next_block:
#                             elements_req=6-len(block)
#                             for j in range(elements_req):
#                                 block.append(next_block.pop(0))

#                             # if next block becomes empty, remove it
#                             if len(next_block) == 0:
#                                 blocks.pop(i + 1)          

#             i += 1


#     print(blocks)
#     for block in blocks:
#         if len(block) < block_size:
#             continue
#         dict={}  
#         dict['date'] = clean_brackets(block[0])
#         dict['value_date'] = clean_brackets(block[1])
#         dict['description'] = block[2]
#         dict['balance'] = clean_brackets(block[3])
#         dict['outgoing'] = clean_brackets(block[4])
#         dict['incoming'] = clean_brackets(block[5])
#         transactions.append(dict)
#         dict={}   
#     return transactions,account_number


def extract_transaction_of_ubl(filepath,page_no,total_no_pages,extract_account=False,previous_balance=None):
    if total_no_pages==0:
        return "No pages to extract transactions"
   
    account_number = None
    
    with open(filepath,"r") as file:
        lines = [line.strip() for line in file if line.strip()]  # remove empty lines
        start_index = 0

        for i, line in enumerate(lines):
            if "** OPENING BALANCE **" in line:
                start_index = i
                break
        if extract_account:
            for i, line in enumerate(lines):
                if "Account Number:" in line:
                    account_number=lines[i+1]
                    break
        if previous_balance is not None:
            current_balance = previous_balance
        else:
            current_balance = lines[start_index+1]        
    if total_no_pages==1:
        skip_lines_from_start=start_index+2  #unwanted header
        skip_lines_from_end=11              #unwanted footer      
    elif page_no==1:
        skip_lines_from_start=start_index+2
        skip_lines_from_end=2
    elif page_no==total_no_pages:
        skip_lines_from_start=9
        skip_lines_from_end=11
    else:
        skip_lines_from_start=9
        skip_lines_from_end=2   
    lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]
  
    transactions=[]
    block_size = 4    #pattern of 6 lines are repeating

    #  # Split lines into initial blocks
    blocks = [lines[i:i + block_size] for i in range(0, len(lines), block_size)]
    for i in range(len(blocks)):
        blocks[i] = [item for item in blocks[i] if not item.strip().isdigit()]

    changed = True
    while changed:
        changed = False
        i = 0
        
        while i < len(blocks):
            #added by 10/11
            # while True:
            inner_count=0
            while inner_count<10:
                inner_count+=1    
                block = blocks[i]
                #added for block protection
                if len(block)<4:
                    if i + 1 < len(blocks):
                        next_block=blocks[i+1]
                        elements_req=4-len(block)
                        for j in range(elements_req):
                            block.append(next_block.pop(0))  
                        # if next block becomes empty, remove it
                        if len(next_block) == 0:
                            blocks.pop(i + 1)    
                #till here  
                if is_number(block[2]) and len(block)==4:
                    break  # if first element is numeric
                if  not is_number(block[2]): # if not numeric 
                    changed = True
                    # merge block[1] and block[2]
                    block[1] = f"{block[1]} {block[2]}".strip()                 
                    block.pop(2)
            

                    # if next block exists, move its 0th element here
                    if i + 1 < len(blocks):
                        next_block = blocks[i + 1]
                        if next_block:
                            elements_req=4-len(block)
                            for j in range(elements_req):
                                block.append(next_block.pop(0))

                            # if next block becomes empty, remove it
                            if len(next_block) == 0:
                                blocks.pop(i + 1) 

            i += 1

    for block in blocks:
        if len(block) < block_size:
            continue
        balance= clean_brackets(block[3])
        dict={} 
        dict['date'] = clean_brackets(block[0])
        dict['description'] = block[1]
        if balance<current_balance:
            dict['outgoing'] = clean_brackets(block[2])
            dict['incoming'] = '-'
        else:
            dict['outgoing'] = '-'
            dict['incoming'] = clean_brackets(block[2])
        dict['balance'] = balance
         
        transactions.append(dict)
        current_balance=balance
        dict={}   
    return transactions,account_number,current_balance

def extract_transaction_of_meezan(filepath, page_no, total_no_pages, extract_account=False):

    if total_no_pages==0 or total_no_pages==1:
        return "No pages to extract transactions"

    account_number = None

    with open(filepath, "r") as file:
        lines = [line.strip() for line in file if line.strip()]

    # -------- ACCOUNT EXTRACTION --------
    
    if extract_account:
        for i, line in enumerate(lines):
            if "Account Number" in line:

                # search next few lines for account number pattern
                for j in range(i, min(i + 10, len(lines))):
                    cleaned = lines[j].replace(" ", "").replace("-", "")

                    if re.fullmatch(r"\d{10,16}", cleaned):
                        account_number = cleaned
                        break

                break

    # -------- FIND TRANSACTION START --------
    start_index = None

    # 1st priority: Opening Balance
    for i, line in enumerate(lines):
        if "<=Opening Balance=>" in line:
            print("opening")
            start_index = i + 3
            break

    # 2nd priority: fallback ONLY if not found
    if start_index is None:
        for i, line in enumerate(lines):
            if "Balance" in line:
                start_index = i + 1
                break


    # -------- FIND TRANSACTION END --------
    if page_no==total_no_pages:
        skip_lines_from_end=12
    else:
        skip_lines_from_end=1

    end_index = len(lines)-skip_lines_from_end
    
    lines = lines[start_index:end_index]
    # print(lines)
    # -------- PARSING --------
    transactions = []
    i = 0

    while i < len(lines):

        # detect DATE + VALUE DATE
        if is_date_of_meezan(lines[i]) and i+1 < len(lines) and is_date_of_meezan(lines[i+1]):
            date = lines[i]
            value_date = lines[i+1]

            j = i + 2
            description_parts = []

            #  KEY LOGIC: everything until first amount = description
            while j < len(lines) and not is_amount(lines[j]):
                description_parts.append(lines[j])
                j += 1

            # safety check
            if j + 2 >= len(lines):
                break

            balance = lines[j]
            debit = lines[j+1]
            credit = lines[j+2]

            description = " ".join(description_parts)

            transactions.append({
                "date": date,
                "value_date": value_date,
                "description": description,
                "balance": balance,
                "outgoing": debit,
                "incoming": credit
            })

            i = j + 3
            continue

        i += 1

    return transactions, account_number


# print(extract_transaction_of_easypaisa("output8.txt",8,12))
# print(extract_transaction_of_easypaisa("output1.txt",1,4))
# print(extract_transaction_of_meezan("output2.txt",2,2))
# print(extract_transaction_of_meezan("output2.txt",2,3))
# extract_transaction_of_meezan("output2.txt",2,3)
# print(extract_transaction_of_ubl("output1.txt",1,1))


def extract_transaction_of_alfalah(filepath,page_no,total_no_pages,extract_account=False,previous_balance=None):
    if total_no_pages==0:
        return "No pages to extract transactions"
   
    account_number = None
    
    with open(filepath,"r") as file:
        lines = [line.strip() for line in file if line.strip()]  # remove empty lines
        start_index = 0

        for i, line in enumerate(lines):
            if "Opening Balance" in line:
                start_index = i
                break
        if extract_account:
            for i, line in enumerate(lines):
                if "Account #" in line:
                    account_number=lines[i+1].replace(" ", "").replace("-", "")
                    break
        if previous_balance is not None:
            current_balance = previous_balance
        else:
            current_balance = clean_amount(lines[start_index+1])    
    
        if total_no_pages==1:
            skip_lines_from_start=start_index+1  #unwanted header
            skip_lines_from_end=7                #unwanted footer      
        elif page_no==1:
            skip_lines_from_start=start_index+1
            skip_lines_from_end=0
        elif page_no==total_no_pages:
            skip_lines_from_start=12
            skip_lines_from_end=7
        else:
            skip_lines_from_start=12
            skip_lines_from_end=0   
        lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]  
     
    
    transactions = []
    i = 0
    
    while i < len(lines):

        line = lines[i]

        # -------- PATTERN 1 --------
        # DATE -> BALANCE -> AMOUNT -> DESCRIPTION
        if is_date(line):

            date = line
            balance = lines[i+1]
            amount = lines[i+2]

            description_lines = []
            j = i + 3

            while j < len(lines) and not is_date(lines[j]) and not is_amount(lines[j]):
                description_lines.append(lines[j])
                j += 1

            description = " ".join(description_lines)

            balance_val = clean_amount(balance)
            amount_val = clean_amount(amount)

            tx = {}
            tx["date"] = date
            tx["description"] = description

            if current_balance is not None and balance_val < current_balance:
                tx["outgoing"] = amount
                tx["incoming"] = "-"
            else:
                tx["outgoing"] = "-"
                tx["incoming"] = amount

            tx["balance"]=balance
            transactions.append(tx)

            current_balance = balance_val
            i = j
            continue


        # -------- PATTERN 2 --------
        # AMOUNT -> DESCRIPTION -> DATE -> BALANCE
        if is_amount(line) and i+3 < len(lines) and is_date(lines[i+2]):

            amount = line
            description = lines[i+1]
            date = lines[i+2]
            balance = lines[i+3]

            balance_val = clean_amount(balance)
            amount_val = clean_amount(amount)

            tx = {}
            tx["date"] = date
            tx["description"] = description

            if current_balance is not None and balance_val < current_balance:
                tx["outgoing"] = amount
                tx["incoming"] = "-"
            else:
                tx["outgoing"] = "-"
                tx["incoming"] = amount

            tx["balance"]=balance
            transactions.append(tx)

            current_balance = balance_val
            i += 4
            continue

        i += 1

    return transactions,account_number,current_balance

# print(extract_transaction_of_alfalah(filepath="output1.txt",extract_account=True))
# print(extract_transaction_of_alfalah("output2.txt",2,2,extract_account=False,previous_balance=16177.97))