import openai
import json
import copy
import re
import time
import os
import shutil
from tqdm import tqdm

maxstep = 100 #最多走幾步
API_key = '' #Enter your key here
thoughts_per_node = 3 #一次幾個candidate
max_output_token = 1500

class Puzzle:
    def __init__(self, file, degree, anslog):
        self.file = json.load(open(file))
        self.train_prompt = '' #題目資訊
        self.source = self.file['source_language'].capitalize()
        self.target = self.file['target_language'].capitalize()
        self.meta = self.file['meta']
        self.answer_board = copy.deepcopy(self.file['test']) #開新的memory紀錄答案
        self.test_len = len(self.answer_board) #題目數量
        self.record = [{} for _ in range(self.test_len)] #紀錄各題的candidate
        self.record_list = [[] for _ in range(self.test_len)] #依certainty以list紀錄各題的candidate,第0個最高
        self.ans_order = [None]* self.test_len #紀錄答題順序for dfs backtrack
        self.curr_level = 0 #樹的層數(ans_order目前步數)
        self.candidate_num = [None]*self.test_len #紀錄目前每一題的candidate是第幾個 0最確定
        self.degree = degree
        self.log = open(anslog, "a")
        
        for i in self.file:
            if i == 'train':
                for j in self.file[i]:
                    self.train_prompt += str(j)[1:-1] + '\n'

    def render_ansboard(self,board): #show出test答題格式
        state = ''
        idx = 1
        for i in board:
            state += str(idx)+ '. ' + str(i) + '\n'
            idx+=1
        return state
    
    def answer_update(self,t_num): #input題號
        print('UPDATE之前:\nansboard:\n',self.answer_board,'\n','record:\n',self.record,'\nrecord_list:\n',self.record_list,'\nanswer_order:\n',self.ans_order,'\ncurr_level:\n',self.curr_level,'\ncandidate_num:\n',self.candidate_num, file = self.log)
        if self.answer_board[t_num-1][2] == '<':
            if self.candidate_num[t_num-1] == None: #還沒有thoughts
                self.candidate_num[t_num-1] = 0
                self.answer_board[t_num-1][0] = self.record_list[t_num-1][0]
            else:
                tmp = self.candidate_num[t_num-1]+1
                self.answer_board[t_num-1][0] = self.record_list[t_num-1][tmp]
                self.candidate_num[t_num-1] = tmp
        else:
            if self.candidate_num[t_num-1] == None: #還沒有thoughts
                self.candidate_num[t_num-1] = 0
                self.answer_board[t_num-1][1] = self.record_list[t_num-1][0]
            else:
                tmp = self.candidate_num[t_num-1]+1
                self.answer_board[t_num-1][1] = self.record_list[t_num-1][tmp]
                self.candidate_num[t_num-1] = tmp
        print('\nUPDATE之後:\nansboard:\n',self.answer_board,'\n','record:\n',self.record,'\nrecord_list:\n',self.record_list,'\nanswer_order:\n',self.ans_order,'\ncurr_level:\n',self.curr_level,'\ncandidate_num:\n',self.candidate_num,file = self.log)
        
    def render_answered(self):
        answered = ''
        for i in range(self.test_len):
            if self.candidate_num[i] != None:
                if self.answer_board[i][2] == '<':    
                    answered += str(i+1) + '. The '+self.source+' translation of the '+self.target+' sentence "'+self.answer_board[i][1]+'" is ['+ self.answer_board[i][0]+ '].\n'
                else:
                    answered += str(i+1) + '. The '+self.target+' translation of the '+self.source+' sentence "'+self.answer_board[i][0]+'" is ['+ self.answer_board[i][1]+ '].\n'
        return answered
    
    def render_not_answered(self):
        unanswered = ''
        for i in range(self.test_len):
            if self.candidate_num[i] == None:
                if self.answer_board[i][2] == '<':    
                    unanswered += str(i+1) + '. The '+self.source+' translation of the '+self.target+' sentence "'+self.answer_board[i][1]+'" is ['+ self.answer_board[i][0]+ '].\n'
                else:
                    unanswered += str(i+1) + '. The '+self.target+' translation of the '+self.source+' sentence "'+self.answer_board[i][0]+'" is ['+ self.answer_board[i][1]+ '].\n'
        return unanswered
    
    def ans_cnt(self):
        cnt = 0
        for i in range(self.test_len): 
            if self.candidate_num[i] != None: cnt+=1
        return cnt

    def backtrack(self):
        t_num = self.ans_order[self.curr_level]
        if self.answer_board[t_num-1][2] == '<':
            self.answer_board[t_num-1][0] = ''
        else:
            self.answer_board[t_num-1][1] = ''
        self.candidate_num[t_num-1] = None
        self.record_list[t_num-1].clear()
        self.record[t_num-1].clear()
        self.ans_order[self.curr_level] = None

def gpt_Err(message):
    try:
        openai.api_key = API_key
        messages = [
            {"role": "user", "content": message}
        ]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",messages=messages, temperature=0.5, 
                                max_tokens=2000, stop=None)
        completed_text = response
        return completed_text #.choices[0].message.content
    except openai.error.ServiceUnavailableError:
        return None
    except openai.error.APIError:
        return None
    except openai.error.Timeout:
        return None

def gpt(prompt):
    maxtry = 5
    tries = 0
    while tries < maxtry:
        completion = gpt_Err(prompt)
        if completion == None:
            print(f'OpenAI server failed, waiting for attempt {tries+1} ...')
            time.sleep(5)
            tries += 1
        else:
            return completion
    if completion == None:
        print(f'Not able to get OpenAI responses after maximum {maxtry} tries')
        return    
            
def candidates_get(Puzzle, text):
    try:
        rowpattern = re.compile(r'(row|Row|row:|Row:)\s*([0-9]{1,})')
        anspattern = re.compile(r'(\[.*\]|\".*\"|\'.*\')\s\((certain|high|medium|low).*\)')
        confidence_to_value = {'certain': 1, 'high': 0.5, 'medium': 0.2, 'low': 0.1}
        rowmatch = re.finditer(rowpattern, text)
        ansmatch = re.finditer(anspattern, text)
        for i in rowmatch:
            Puzzle.ans_order[Puzzle.curr_level] = int(i.group(2))
            break
        t_num = Puzzle.ans_order[Puzzle.curr_level] #題號
        if Puzzle.candidate_num[t_num-1] != None:
            return t_num
        for i in ansmatch:
            print('finding... ',file = Puzzle.log)
            print(i.group(1),'\n',file = Puzzle.log)
            Puzzle.record[t_num-1][i.group(1)[1:-1]] = confidence_to_value.get(i.group(2))
        Puzzle.record_list[t_num-1] = sorted(Puzzle.record[t_num-1], key=Puzzle.record[t_num-1].get, reverse=True)
        if(len(Puzzle.record_list[t_num-1]) == 0):
            raise TypeError('Failed')
        print('TryCandidateget:',Puzzle.record_list[t_num-1],'\n',file = Puzzle.log)
        return t_num
    except:
        rowpattern = re.compile(r'([0-9]{1,})')
        anspattern = re.compile(r'(\[.*\]\s|\".*\"\s|\s.*\s)\((certain|high|medium|low).*\)')
        confidence_to_value = {'certain': 1, 'high': 0.5, 'medium': 0.2, 'low': 0.1}
        rowmatch = re.finditer(rowpattern, text)
        ansmatch = re.finditer(anspattern, text)
        for i in rowmatch:
            Puzzle.ans_order[Puzzle.curr_level] = int(i.group(1))
            break
        t_num = Puzzle.ans_order[Puzzle.curr_level] #題號
        if Puzzle.candidate_num[t_num-1] != None:
            return t_num
        for i in ansmatch:
            print('finding... ',file = Puzzle.log)
            print(i.group(1),'\n',file = Puzzle.log)
            Puzzle.record[t_num-1][i.group(1)[1:-1]] = confidence_to_value.get(i.group(2))
        Puzzle.record_list[t_num-1] = sorted(Puzzle.record[t_num-1], key=Puzzle.record[t_num-1].get, reverse=True)
        print('exCandidateget:',Puzzle.record_list[t_num-1],'\n',file = Puzzle.log)
        return t_num
    
def ensure_candidates(Puzzle, t_num, tokens, degree, prop_prompt, cur_step, pbar, GPTprop):
    while len(Puzzle.record_list[t_num-1]) != degree:
        Puzzle.record[t_num-1].clear()
        Puzzle.record_list[t_num-1].clear()
        Puzzle.ans_order[Puzzle.curr_level] = None
        print('Ensuring the number of candidates equals to degree...\n',file = Puzzle.log)
        prop_res = gpt(prop_prompt)
        print(prop_res,file = Puzzle.log)
        print(prop_res.choices[0].message.content,file = Puzzle.log)
        tokens[0]+=prop_res['usage']['prompt_tokens']
        tokens[1]+=prop_res['usage']['completion_tokens']
        cur_step += 1
        pbar.update(1)
        t_num = candidates_get(Puzzle,prop_res.choices[0].message.content) 
        GPTprop.append('ensure_candidate'+ prop_res.choices[0].message.content)#json
        if Puzzle.candidate_num[t_num-1] != None:
            return t_num, cur_step
    return t_num, cur_step

def evaluation_get(Puzzle, res, count):
    evapattern = re.compile(r'.*\((Sure|Maybe|Impossible)\)')
    evamatch = re.finditer(evapattern, res)
    for i in evamatch:
        count[i.group(1)]+=1
        
def GPT_token_fee(Model, tokens):
    note = {'total input tokens': tokens[0], 'total output tokens': tokens[1], 'total fee': 0}
    if Model == 'gpt-3.5':
        note['total fee']+= (tokens[0]*0.0015 + tokens[1]*0.002)/1000
    elif Model == 'gpt-4':
        note['total fee']+= (tokens[0]*0.03 + tokens[1]*0.06)/1000
    return note

propose_prompt = '''Translation Puzzle: {source} and {target}

Below is a translation puzzle where you are given {source} sentences and their corresponding {target} translations in Train Set. 
The goal is to translate the provided {source} sentences into {target} or translate the provided {target} sentences into {source}

meta: {meta}

Train Set:
{trainprompt}
Giving the current answered board:(Not guaranteed to be correct, empty if all not yet answered):
{answerboard}
Please solve the following translation puzzles:
{unanswered}
Please provide the translation for ONLY ONE unanswered row of your choice.
You do not need to answer more than one row.

List {degree} possible answers for the selected row with your confidence levels (certain/high/medium/low) based on the provided train set and meta above.

Here are two examples of the format of all possible answers for the selected row n:

Example 1.
n.The Wambaya translation for English sentence "I see you." is [].

Row n
[Ngarlu nya.] (certain)
[Ngajbi nginya.] (medium)
[Gulugba ngu.] (low)

Example 2.
n.The english translation for wambaya sentence "Ngarlu nya." is [].

Row n
[I see you.] (certain)
[I saw you.] (medium)
[You are seen.] (low)

You should always add [] to your answer.
'''


value_prompt = '''
Below is a translation puzzle between {source} and {target},
'meta' is a hint giving some helpful information for translating.
The train set is known {source} corresponding to its translation in {source}.
meta: {meta}
Train set:

{trainprompt}

The test set are current attempts, please evaluate whether they are correct translations using (Sure|Maybe|Impossible).
Your output format should be like:

1. The wambaya translation for english sentence "I will sleep." is [Gulugba ngu.]. (Sure)
5.  The english translation for wambaya sentence "Ngarlu nya." is [You danced.]. (Maybe)
7.  The english translation for wambaya sentence "Ngajbi nginya." is [I see you]. (Impossible)
11. The wambaya translation for english sentence "…" is […]. (Sure|Maybe|Impossible)

Please only evaluate the {ans_num} sentences below:

Test Set:
{answerboard}
'''

def dfs(Puzzle, step_limit, diary, tokens):
    cur_step = 0
    deepest = 0
    cache = None
    pbar = tqdm(desc = 'while loop', total = step_limit)
    while cur_step < step_limit:
        print('tokens:',tokens)
        GPTprop = []
        GPTeva = []
        Ansboard_status = []
        bt = False
        prop_prompt = propose_prompt.format(source = Puzzle.source, target = Puzzle.target, meta = Puzzle.meta, trainprompt = Puzzle.train_prompt, degree = Puzzle.degree, unanswered = Puzzle.render_not_answered(), answerboard = Puzzle.render_answered())
        prop_res = gpt(prop_prompt)
        print(prop_res,file = Puzzle.log)
        print(prop_res.choices[0].message.content,file = Puzzle.log)
        tokens[0]+=prop_res['usage']['prompt_tokens']
        tokens[1]+=prop_res['usage']['completion_tokens']
        cur_step += 1
        pbar.update(1)
        t_num = candidates_get(Puzzle,prop_res.choices[0].message.content) 
        GPTprop.append(prop_res.choices[0].message.content)#json
        t_num, cur_step = ensure_candidates(Puzzle, t_num, tokens, Puzzle.degree, prop_prompt, cur_step, pbar, GPTprop)
        while Puzzle.candidate_num[t_num-1] != None:
            prop_res = gpt(prop_prompt)
            print(prop_res,file = Puzzle.log)
            print(prop_res.choices[0].message.content,file = Puzzle.log)
            tokens[0]+=prop_res['usage']['prompt_tokens']
            tokens[1]+=prop_res['usage']['completion_tokens']
            print('tokens:',tokens)
            cur_step += 1
            pbar.update(1)
            t_num = candidates_get(Puzzle,prop_res.choices[0].message.content)
            GPTprop.append(prop_res.choices[0].message.content)#json
            t_num, cur_step = ensure_candidates(Puzzle, t_num, tokens, Puzzle.degree, prop_prompt, cur_step, pbar, GPTprop)
        Puzzle.answer_update(t_num)
        Ansboard_status.append(Puzzle.answer_board)#json
        Puzzle.ans_order[Puzzle.curr_level] = t_num #題號
        eva_prompt = value_prompt.format(source = Puzzle.source, target = Puzzle.target, meta = Puzzle.meta, trainprompt = Puzzle.train_prompt, ans_num = Puzzle.ans_cnt() ,answerboard = Puzzle.render_answered())
        eva_res = gpt(eva_prompt)
        print(eva_res,file = Puzzle.log)
        print(eva_res.choices[0].message.content,file = Puzzle.log)
        tokens[0]+=eva_res['usage']['prompt_tokens']
        tokens[1]+=eva_res['usage']['completion_tokens']
        GPTeva.append(eva_res.choices[0].message.content)#json
        count = {'Sure': 0, 'Maybe':0 ,'Impossible':0}
        evaluation_get(Puzzle,eva_res.choices[0].message.content, count)
        while count['Impossible'] != 0:
            while Puzzle.candidate_num[t_num-1]+1 != Puzzle.degree:
                count = {'Sure': 0, 'Maybe':0 ,'Impossible':0}
                Puzzle.answer_update(t_num)
                Ansboard_status.append(Puzzle.answer_board)#json
                eva_prompt = value_prompt.format(source = Puzzle.source, target = Puzzle.target, meta = Puzzle.meta, trainprompt = Puzzle.train_prompt, ans_num = Puzzle.ans_cnt() ,answerboard = Puzzle.render_answered())
                eva_res = gpt(eva_prompt)
                print(eva_res,file = Puzzle.log)
                print(eva_res.choices[0].message.content,file = Puzzle.log)
                tokens[0]+=eva_res['usage']['prompt_tokens']
                tokens[1]+=eva_res['usage']['completion_tokens']
                GPTeva.append(eva_res.choices[0].message.content)#json
                evaluation_get(Puzzle,eva_res.choices[0].message.content, count)
                if count['Impossible'] == 0:
                    bt = False #Mark
                    break
            if count['Impossible'] == 0:
                break
            if Puzzle.candidate_num[t_num-1]+1 == Puzzle.degree:
                Puzzle.backtrack()
                bt = True
                if Puzzle.curr_level != 0:
                    Puzzle.curr_level -= 1
                    t_num = Puzzle.ans_order[Puzzle.curr_level]
                else:
                    count = {'Sure': 0, 'Maybe':0 ,'Impossible':0}
                    break
        if deepest < Puzzle.ans_cnt():
            deepest = Puzzle.ans_cnt()
            cache = copy.deepcopy(Puzzle.answer_board)
        if Puzzle.ans_cnt() == Puzzle.test_len:
            print('Answer_done.\n',Puzzle.answer_board)
            print('Answer_done.\n',Puzzle.answer_board,file = Puzzle.log)
            pbar.update(step_limit - cur_step)
            info = {'Step:': str(cur_step) ,'GPT propose response:': GPTprop, 'GPT evaluation response:': GPTeva , 'Answer Board Change:': Ansboard_status, 'Deepest State:': cache}
            diary.append(info)
            return Puzzle.answer_board
        elif cur_step >= step_limit:
            print('step_limit reached.\n',Puzzle.answer_board)
            print('step_limit reached.\n',Puzzle.answer_board,file = Puzzle.log)
            info = {'Step:': str(cur_step) ,'GPT propose response:': GPTprop, 'GPT evaluation response:': GPTeva , 'Answer Board Change:': Ansboard_status, 'Deepest State:': cache}
            diary.append(info)
            return cache
        if not bt:
            Puzzle.curr_level += 1
        info = {'Step:': str(cur_step) ,'GPT propose response:': GPTprop, 'GPT evaluation response:': GPTeva , 'Answer Board Change:': Ansboard_status, 'Deepest State:': cache}
        diary.append(info)

path = 'sectest'
dir_list = os.listdir(path)
for i in range(len(dir_list)):
    if dir_list[i] == '.DS_Store':
        dir_list.pop(i)
        break

total_fee = 0
for i in tqdm(range(len(dir_list))):
    add = f'sectest/{dir_list[i]}'#輸入位置
    des = f'secrec/{dir_list[i]}' #輸出位置
    ansform = f'secans/{dir_list[i]}'
    anslog = f'seclog/{dir_list[i]}.txt'
    print(dir_list[i],'\n')
    a = Puzzle(add, thoughts_per_node,anslog)
    print(a.source,'\n')
    diary = []
    tokens = [0,0]
    final_ans = dfs(a,maxstep,diary,tokens)
    with open(des, 'w', encoding='utf8') as fout:
        json.dump(diary, fout, indent = 5, ensure_ascii=False)
    print('Fee:',GPT_token_fee("gpt-3.5", tokens))
    total_fee += GPT_token_fee("gpt-3.5", tokens)['total fee']
    print('\nTotal Fee:',total_fee,'USD/',total_fee*31.72,'NTD')
    with open(add, 'r+', encoding='utf8') as js:
        data = json.load(js)
        data['test']= final_ans
        js.seek(0)
        json.dump(data, js, indent=5, ensure_ascii=False)
    shutil.copyfile(add,ansform)
    os.remove(f'sectest/{dir_list[i]}')