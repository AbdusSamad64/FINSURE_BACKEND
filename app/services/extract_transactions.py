from app.utils.extraction_helpers import clean_brackets,is_number,is_int_convertible
def extract_transaction_of_easypaisa(filepath,page_no,total_no_pages):
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
    lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]
    
    transactions=[]
    block_size = 24    #pattern of 24 lines are repeating

     # Split lines into initial blocks
    blocks = [lines[i:i + block_size] for i in range(0, len(lines), block_size)]
    # print(blocks)
    # changing by abdullah
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
    return transactions

def extract_transaction_of_meezan(filepath,page_no,total_no_pages):
    if total_no_pages==0 or total_no_pages==1:
        return "No pages to extract transactions"
    else:
        skip_lines_from_start=29
        skip_lines_from_end=12

    with open(filepath,"r") as file:
        lines = [line.strip() for line in file if line.strip()]  # remove empty lines
   
    if (is_int_convertible(lines[8])==True and lines[7]!='MEEZAN KAFALAH ACCOUNT'):
        lines = lines[skip_lines_from_start:len(lines)-skip_lines_from_end]
    elif lines[7]=='MEEZAN KAFALAH ACCOUNT':
        lines = lines[skip_lines_from_start-1:len(lines)-skip_lines_from_end]   
    else:
        lines = lines[skip_lines_from_start+1:len(lines)-skip_lines_from_end]   

    
    transactions=[]
    block_size = 6    #pattern of 6 lines are repeating

    #  # Split lines into initial blocks
    blocks = [lines[i:i + block_size] for i in range(0, len(lines), block_size)]
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
                    # print("detected less blocks")
                    if i + 1 < len(blocks):
                        next_block=blocks[i+1]
                        elements_req=6-len(block)
                        for j in range(elements_req):
                            block.append(next_block.pop(0))  
                        # if next block becomes empty, remove it
                        if len(next_block) == 0:
                            blocks.pop(i + 1)    
                #till here      
                if is_number(block[3]) and len(block)==6:
                    break  # if first element is numeric
                if  not is_number(block[3]): # if not numeric 
                    changed = True
                    # merge block[2] and block[3]
                    block[2] = f"{block[2]} {block[3]}".strip()
                    block.pop(3)

                    # if next block exists, move its 0th element here
                    if i + 1 < len(blocks):
                        next_block = blocks[i + 1]
                        if next_block:
                            elements_req=6-len(block)
                            for j in range(elements_req):
                                block.append(next_block.pop(0))

                            # if next block becomes empty, remove it
                            if len(next_block) == 0:
                                blocks.pop(i + 1)          

            i += 1


    
    for block in blocks:
        if len(block) < block_size:
            continue
        dict={}  
        dict['date'] = clean_brackets(block[0])
        dict['value_date'] = clean_brackets(block[1])
        dict['description'] = block[2]
        dict['balance'] = clean_brackets(block[3])
        dict['outgoing'] = clean_brackets(block[4])
        dict['incoming'] = clean_brackets(block[5])
        transactions.append(dict)
        dict={}   
    return transactions




# print(extract_transaction_of_easypaisa("output8.txt",8,12))
# print(extract_transaction_of_easypaisa("output4.txt",4,4))
# print(extract_transaction_of_meezan("output2.txt",2,2))