import openai
import json
import copy
import re
import time
from tqdm import tqdm
import os

API_key = os.getenv("OPENAI_API_KEY", "")
max_output_token = 1500

class Puzzle:
    def __init__(self, file):
        self.file = json.load(open(file))
        self.train_prompt = '' #題目資訊
        self.source = self.file['source_language'].capitalize()
        self.target = self.file['target_language'].capitalize()
        self.meta = self.file['meta']
        self.answer_board = copy.deepcopy(self.file['test']) #開新的memory紀錄答案
        self.test_len = len(self.answer_board) #題目數量
        for i in self.file:
            if i == 'train':
                for j in self.file[i]:
                    self.train_prompt += str(j)[1:-1] + '\n'

    def answer_update(self,ans_list): #input題號
        for i in range(self.test_len):
            if self.answer_board[i][2] == '<':
                self.answer_board[i][0] = ans_list[i]
            else:
                self.answer_board[i][1] = ans_list[i]
    
    def render_not_answered(self):
        unanswered = ''
        for i in range(self.test_len):
            if self.answer_board[i][2] == '<':    
                unanswered += str(i+1) + '. The '+self.source+' translation of the '+self.target+' sentence "'+self.answer_board[i][1]+'" is ['+ self.answer_board[i][0]+ '].\n'
            else:
                unanswered += str(i+1) + '. The '+self.target+' translation of the '+self.source+' sentence "'+self.answer_board[i][0]+'" is ['+ self.answer_board[i][1]+ '].\n'
        return unanswered

def gpt_Err(message):
    try:
        openai.api_key = API_key
        messages = [
            {"role": "user", "content": message}
        ]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo",messages=messages, temperature=0.7, 
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
    anspattern = re.compile(r'is\s(\".*\"|\[.*\]|\'.*\')')
    ansmatch = re.finditer(anspattern, text)
    ans_list = []
    for i in ansmatch:
        ans_list.append(i.group(1)[1:-1])
    Puzzle.answer_update(ans_list)

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
Please solve the following translation puzzles:
{unanswered}
Please provide translation for all unanswered row.
Your answer form should be like:
1. your answer for problem 1
2. your answer for problem 2
...
n. your answer for problem n
'''

path = "test"
dir_list = os.listdir(path)
for i in range(len(dir_list)):
    if dir_list[i] == '.DS_Store':
        dir_list.pop(i)
        break

total_fee = 0
for i in tqdm(range(len(dir_list))):
    tokens = [0,0]
    add = f'test/{dir_list[i]}'#輸入位置
    ansform = f'ans/{dir_list[i]}'
    print(dir_list[i])
    try:
        a = Puzzle(add)
        prop_prompt = propose_prompt.format(source = a.source, target = a.target, meta = a.meta, trainprompt = a.train_prompt, unanswered = a.render_not_answered())
        res = gpt(prop_prompt)
        tokens[0]+=res['usage']['prompt_tokens']
        tokens[1]+=res['usage']['completion_tokens']
        candidates_get(a, res.choices[0].message.content)
        print(res.choices[0].message.content)
        final_ans = a.answer_board
        with open(ansform, 'r+', encoding='utf8') as js:
            data = json.load(js)
            data['test']= final_ans
            js.seek(0)
            json.dump(data, js, indent=5, ensure_ascii=False)
        os.remove(f'test/{dir_list[i]}')
        total_fee += GPT_token_fee("gpt-3.5", tokens)['total fee']
        print('\nTotal Fee:',total_fee,'USD/',total_fee*31.72,'NTD')
    except:
        print(res.choices[0].message.content)
        total_fee += GPT_token_fee("gpt-3.5", tokens)['total fee']
        print('\nTotal Fee:',total_fee,'USD/',total_fee*31.72,'NTD')
