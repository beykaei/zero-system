import pandas as pd
import openai
import ast
from datetime import datetime


def answer_question_gpt(
        dict_prompt,
        model='text-davinci-003',  # GPT-3.5
        max_tokens=1000,
        stop_sequence=None,
        temperature=0,
        top_p=0.2,
        frequency_penalty=0,
        presence_penalty=0,
        api_key=None
):
    openai.api_key = api_key
    prompt = f"""
            {dict_prompt['system']}
            Context:\n```{dict_prompt['context']}```
    """
    max_iteration = 5

    for attempt in range(max_iteration):
        try:
            response = openai.Completion.create(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop_sequence,
                model=model,
            )

            dict_prompt['response'] = response['choices'][0]['text'].strip()
            break
        except Exception as e:
            print(f'Attempt {attempt + 1} failed, retrying...')
            print(e)

    return dict_prompt


def parse_response(response):
    try:
        response = ast.literal_eval(response)
    except:
        try:
            response_json = response[response.rfind('{'): response.rfind('}') + 1]
            response = ast.literal_eval(response_json)
        except Exception as e:
            print(str(e))
            pass

    return response


def get_date(s_date):
    date_patterns = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]

    for pattern in date_patterns:
        try:
            dd = datetime.strptime(s_date, pattern).date()
            return pattern
        except:
            pass


def convert_date_column(df, pattern=None):
    date_pattern = None
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                pattern1 = get_date(str(df[col].iloc[0]))
                if pattern1: date_pattern = pattern1
                if not pattern: pattern = pattern1
                df[col] = pd.to_datetime(df[col], format=pattern1).dt.strftime(pattern)
            except ValueError:
                pass

    return df, date_pattern


def generate_sample_dic(df):
    smp_dict = {}
    for clm in df.columns:
        smp_dict[clm] = list(df[clm].head(3).values)

    return smp_dict


def gpt_clms_mapping(df, df_template, api_key):
    clm_maps = {}
    template_clms = list(df_template.columns)
    table_clms = list(df.columns)
    table_A_dict = generate_sample_dic(df)
    template_dict = generate_sample_dic(df_template)

    for clm in table_clms:
        clm_values = table_A_dict[clm]
        dict_prompt = {
            'system': 'You are expert in matching table columns.',
            'context': f'There are list of two columns from two tables. \
                One is a template table and the column names are: {template_clms}. \
                Here is an example of values in each column for the template table in the dictionary format in which the key is the column name and value is a list of sample values: \n\
                    {template_dict}. \n\
                The second table we want to find the best match of a column from the template table. \
                Here is an example of values of the column {clm} for the second table: \n\
                    {clm_values}. \n\
                Find the best match for the column of the second table from template table columns based on the example values.\
                If there is not a good match response with None. \
                Fource output in the python dictionary format in which key is the `Answer` and the value is the best column name found.\
                '''
        }
        response = answer_question_gpt(dict_prompt=dict_prompt, api_key=api_key)

        clm_maps[clm] = parse_response(response['response'])['Answer']

    return clm_maps


def parse_name_prompt(values, api_key):
    dict_prompt = {
        'system': 'You are expert in detecting first and last name.',
        'context': f'Based on the values bellow, find if all of them `first name`, `last name`, or `first and last name`. \n \
                    Values: {values} \n \
                    Fource output in the python dictionary format with one key in which key is the `Answer` and the value is \
                    one of these [`first name`, `last name`, or `first and last name`]'
    }
    response = answer_question_gpt(dict_prompt=dict_prompt, api_key=api_key)

    return parse_response(response['response'])['Answer']


def parse_mapping(columns_map, table_A, api_key):
    name_values = {}
    df = pd.DataFrame()
    for key, value in columns_map.items():
        if value is None:
            df[key] = table_A[key]
        else:
            if value == 'EmployeeName':
                response = parse_name_prompt(table_A.head(5)[key].values, api_key)
                name_values[response] = table_A[key]
            elif value not in df.columns:
                df[value] = table_A[key]

        if 'first and last name' in name_values:
            df['EmployeeName'] = name_values['first and last name']
        elif 'first name' in name_values and 'last name' in name_values:
            df['EmployeeName'] = name_values['first name'] + ' ' + name_values['last name']
        elif 'first name' in name_values:
            df['EmployeeName'] = name_values['first name']
        elif 'last name' in name_values:
            df['EmployeeName'] = name_values['last name']

    return df


def match_columns_format(df1, df2):
    for value in df1.columns:
        if value is not None:
            try:
                print(f'Column {value}')
                df2[value] = df2[value].astype(df1[value].dtypes.name)
                print('-- done!')
            except Exception as err:
                print(f'-- There is an error: {err}')
                pass

    return df2
