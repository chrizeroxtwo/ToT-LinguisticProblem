import openai
import json
from tqdm import tqdm
import shutil
import os
import time

class puzzle:
    def __init__(self, file):
        self.file = json.load(open(file))
        self.train = ''
        for j in self.file['train']:
            self.train += str(j) + '\n'
        self.test = ''
        for i in self.file['test']:
            self.test += str(i[0:2]) + '\n'
        self.rules = None
        self.final = None

def gpt_Err(message):
    try:
        openai.api_key = os.getenv("OPENAI_API_KEY", "")
        messages = [
            {"role": "user", "content": message}
        ]
        response = openai.ChatCompletion.create(model="gpt-4",messages=messages, temperature=0.7, 
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

stage_1_prompt = '''
I have a linguistic puzzle that in a form of Rosetta Stone, namely, given a set of known translation between two languages, the goal is to translate the sets that one of each language correspondences are missing. If there's a team that aims to solve the puzzle, what kind of experts do you recommend? Ideally there will be just 3 people in the team.
Also, your response should be shorter than 50 words.
'''

stage_2_prompt = '''
{GPT_response}
Assuming there are 3 experts, as described above. One day they 
encountered a language puzzle with a certain amount of known sets 
which includes the unknown language and its corresponding English 
translations. Their goal is to figure out the lost parts of the set 
with its unknown language pairs disappeared and the set with its 
English pairs gone. Below is the known sets of unknown language and 
its corresponding English translations. 
Known Set:
{Train}
They first have to summarize rules of train set in order to solve the puzzle.
Please show their discussion.
'''

stage_3_prompt = '''
{GPT_response_1}
Assuming there are 3 experts, as described above. One day they 
encountered a language puzzle with a certain amount of known sets 
which includes the unknown language and its corresponding English 
translations. Their goal is to figure out the lost parts of the set 
with its unknown language pairs disappeared and the set with its 
English pairs gone. Below is the known sets of unknown language and 
its corresponding English translations. 
Known Set:
{Train}
They first have to summarize rules of train set in order to solve the puzzle.
And below is their discussion on summarizing rules.
{GPT_response_2}
And below is the puzzle needs to be decoded.
{Test}
Please show their discussion and final answer.
'''

res_one = '''1. Linguist
2. Data Scientist
3. Cryptanalyst
'''

def GPT_token_fee(Model, tokens):
    note = {'total input tokens': tokens[0], 'total output tokens': tokens[1], 'total fee': 0}
    if Model == 'gpt-3.5':
        note['total fee']+= (tokens[0]*0.0015 + tokens[1]*0.002)/1000
    elif Model == 'gpt-4':
        note['total fee']+= (tokens[0]*0.03 + tokens[1]*0.06)/1000
    return note

def Conference(puzzle, tokens):
    res_1 = gpt(stage_2_prompt.format(GPT_response = res_one, Train = puzzle.train))
    puzzle.rules = res_1.choices[0].message.content
    tokens[0]+=res_1['usage']['prompt_tokens']
    tokens[1]+=res_1['usage']['completion_tokens']
    print(puzzle.rules)
    res_2 = gpt(stage_3_prompt.format(GPT_response_1 = res_one, Train = puzzle.train, GPT_response_2 = puzzle.rules, Test = puzzle.test))
    puzzle.final = res_2.choices[0].message.content
    tokens[0]+=res_2['usage']['prompt_tokens']
    tokens[1]+=res_2['usage']['completion_tokens']
    print(puzzle.final)
    
path = 'Advanced_'
dir_list = os.listdir(path)
for i in range(len(dir_list)):
    if dir_list[i] == '.DS_Store':
        dir_list.pop(i)
        break
print(dir_list)

total_fee = 0
for i in tqdm(range(len(dir_list))):
    tokens = [0,0]
    a = puzzle(f'Advanced_/{dir_list[i]}')
    Conference(a, tokens)
    #print('----------------------------')
    #print(a.train)
    #print(a.test)
    #print(stage_2_prompt.format(GPT_response = res_one, Train = a.train))
    #print(stage_3_prompt.format(GPT_response_1 = res_one, Train = a.train, GPT_response_2 = a.rules, Test = a.test))
    #print('Fee:',GPT_token_fee("gpt-4", tokens))
    total_fee += GPT_token_fee("gpt-4", tokens)['total fee']
    print('\nTotal Fee:',total_fee,'USD/',total_fee*31.72,'NTD')
