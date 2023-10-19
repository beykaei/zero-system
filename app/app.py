import streamlit as st
import pandas as pd

from process import convert_date_column, gpt_clms_mapping, parse_mapping, match_columns_format

st.title('Input Data:')
openai_api_key = st.text_input('OpenAI API Key')

st.title('Upload Tables:')
table_A = table_template = None
table = st.file_uploader("Upload Template Table", type={"csv", "txt"})
if table is not None:
    table_template = pd.read_csv(table)
    table_template, date_pattern = convert_date_column(table_template)
    st.header('Template Table')
    st.write(table_template.head(5))
else:
    st.write('Table not recognized!')

table = st.file_uploader("Upload Mapping Table", type={"csv", "txt"})
if table and table_template is not None:
    table_A = pd.read_csv(table)
    table_A, dp = convert_date_column(table_A, date_pattern)
    st.header('Target Table')
    st.write(table_A)
else:
    st.write('Table not recognized!')


@st.cache_data
def run_mapping():
    if table_A is not None and table_template is not None and openai_api_key != '':
        clm_map = gpt_clms_mapping(table_A, table_template, openai_api_key)
        st.header('Mapping results:')
        # st.write(columns_map)
        return clm_map
    else:
        st.write('Please upload tables and provide OpenAI API_KEY!')


def change_mapping(**kwargs):
    st.session_state['clm_map'][kwargs['clm']] = st.session_state[kwargs['clm']]


if "mnc" not in st.session_state:
    st.session_state.mnc = False
if "apm" not in st.session_state:
    st.session_state.apm = False
if "clm_map" not in st.session_state:
    st.session_state.clm_map = False


st.title('Map Target Column')
st.write('This will find the best match for each column in the target table.')
st.write('The target column format will be automatically detected and transformed from Template table.')
if st.button(label='Run Mapping', type='primary') or st.session_state.mnc:
    clm_map = run_mapping()
    st.session_state['clm_map'] = clm_map
    template_clms = list(table_template.columns)
    for clm in table_A.columns:
        if clm_map[clm]:
            ll = [clm_map[clm]]
            ll1 = template_clms.copy()
            ll1.remove(clm_map[clm])
            ll.extend(ll1 + [None])
        else:
            ll = [clm_map[clm]]
            ll.extend(template_clms)
        clm_selected = st.selectbox(clm, ll, on_change=change_mapping,
                                    kwargs={'clm': clm}, key=clm)
    st.session_state.mnc = True


if st.session_state.mnc:
    st.title('Apply Mapping')
    if st.button(label='Apply Mapping', type='primary'):
        st.write(st.session_state['clm_map'])
        columns_map = st.session_state['clm_map']
        new_table = parse_mapping(columns_map, table_A, openai_api_key)
        new_table = match_columns_format(table_template, new_table)

        st.write(new_table)
        new_table = new_table.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download table as CSV",
            data=new_table,
            file_name='new_table.csv',
            key="download-tools-csv",
        )
        st.session_state.apm = True


if st.session_state.apm:
    st.title('Submit Map dict. for Training')
    if st.button(label='Submit Mapping Dictionary', type='primary'):
        columns_map = st.session_state['clm_map']
        row_list = []
        for key, val in columns_map.items():
            row = [key, val, str(table_A[key].head(3).values.tolist()),
                   str(table_template[val].head(3).values.tolist()) if val else None]
            row_list.append(row)

        clm_name = ['target_name', 'map_name', 'target_samples', 'map_samples']
        df_train = pd.DataFrame(row_list, columns=clm_name)
        st.write(df_train)
        df_train = df_train.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download table as CSV",
            data=df_train,
            file_name='new_table.csv',
            key="download-trains-csv",
        )


def clear_cache():
    st.session_state.mnc = False
    st.session_state.mfc = False
    st.session_state.apm = False
    st.cache_data.clear()
    st.cache_resource.clear()


st.sidebar.button("Refresh Program", on_click=clear_cache)
