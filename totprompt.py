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