# Solving Linguistic Olympiad Problems with Tree-of-Thought Prompting
This is the official impletmentation of Rocling2023 Paper "Solving Linguistic Olympiad Problems with Tree-of-Thought Prompting".
The dataset for the experiment in the paper please refer to https://ukplab.github.io/PuzzLing-Machines/ by Şahin et al. (2020).
For the dataset for the experiment in the paper please refer to https://ukplab.github.io/PuzzLing-Machines/ by Şahin et al. (2020).
We will update and optimize this repository recently.

## Setup
1. Install `ToT-LinguisticProblem` packages by:
```
git clone https://github.com/chrizeroxtwo/ToT-LinguisticProblem.git
cd ToT-LinguisticProblem
pip install -r requirements.txt
```
2. Store your OpenAI API key in environment variable `OPENAI_API_KEY`.
3. Install dataset `Competition Data` from https://ukplab.github.io/PuzzLing-Machines/ 

## Paper Experiment Result
`Experiment_Result` directory contains the result of the experiment with 6 different method and parameters.

`Revised_tot_tmp5` refers to Tree-of-Thought without step limit (Temperature = 0.5).

`Revised_tot_tmp7` refers to Tree-of-Thought without step limit (Temperature = 0.7).

`tot_tmp5` refers to Tree-of-Thought with step limit (Temperature = 0.5).

`tot_tmp7` refers to Tree-of-Thought with step limit (Temperature = 0.7).

`StdIO_temp_0.5` refers to baseline Standard Input-Output Prompting (Temperature = 0.5).

`StdIO_temp_0.7` refers to baseline Standard Input-Output Prompting (Temperature = 0.7).