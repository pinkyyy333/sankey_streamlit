import streamlit as st
import pandas as pd
from pyecharts.charts import Sankey
from pyecharts import options as opts
from pyecharts.globals import CurrentConfig
from streamlit_echarts import st_pyecharts

CurrentConfig.ONLINE_HOST = "https://cdn.jsdelivr.net/npm/echarts@latest/dist/"

st.markdown("""
    <style>
        body {
            font-family: 'Times New Roman', sans-serif;
        }
        .main {
            font-size: 18px;
        }
        .footer {
            font-size: 14px;
            text-align: center;
            margin-top: 30px;
            color: #555;
        }
    </style>
""", unsafe_allow_html=True)


st.title("成員工時調查-Sankey Chart 產生器")
st.write("請上傳 Excel 檔案，系統會自動產生 Sankey 圖表")

def options_select():
    if "selected_names" in st.session_state:
        if -1 in st.session_state["selected_names"]:
            st.session_state["selected_names"] = unique_names.tolist()  # 全選時自動選擇所有使用者
        else:
            st.session_state["max_selections"] = len(unique_names)  # 顯示所有選項

uploaded_file = st.file_uploader("上傳 Excel 檔案", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    required_columns = ["姓名", "公務預算工時總計", "專案任務工時總計"]
    if not all(col in df.columns for col in required_columns):
        st.error("Excel 檔案缺少必要的欄位！請確認欄位名稱是否正確。")
    else:
        unique_names = df["姓名"].unique()
        if "max_selections" not in st.session_state:
            st.session_state["max_selections"] = len(unique_names)
        
        options = [-1] + list(unique_names)
        selected_names = st.multiselect(
            label="選擇要顯示的使用者",
            options=options,
            key="selected_names",
            max_selections=st.session_state["max_selections"],
            on_change=options_select,
            format_func=lambda x: "全選" if x == -1 else f"{x}",
            default=unique_names[:5],
        )
        if -1 in selected_names:
            selected_names = unique_names.tolist()
            
        df = df[df["姓名"].isin(selected_names)]

        office_start_idx = df.columns.get_loc("公務預算工時總計") + 1
        project_start_idx = df.columns.get_loc("專案任務工時總計") + 1
        office_end_idx = df.columns.get_loc("專案任務工時總計")
        office_cols = df.columns[office_start_idx:office_end_idx]
        project_end_idx = len(df.columns)
        project_cols = df.columns[project_start_idx:project_end_idx]
        
        df[office_cols] = df[office_cols].astype(str).replace("nan", "")
        df[project_cols] = df[project_cols].astype(str).replace("nan", "")
        
        # 讀取組別資訊
        df_long_office = df.melt(id_vars=["組別", "姓名"], value_vars=office_cols, var_name="小總類", value_name="value")
        df_long_office["大總類"] = "公務預算工時總計"

        df_long_project = df.melt(id_vars=["組別", "姓名"], value_vars=project_cols, var_name="小總類", value_name="value")
        df_long_project["大總類"] = "專案任務工時總計"

        df_long = pd.concat([df_long_office, df_long_project])
        df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
        df_long = df_long[df_long["value"] > 0]
        df_long["value"] = df_long["value"].fillna(0)
        # 計算各層級的工時總計
        group_agg = df_long.groupby(["大總類", "組別"])["value"].sum().reset_index()
        group_sub_agg = df_long.groupby(["組別", "小總類"])["value"].sum().reset_index()
        
        # 建立節點
        nodes = (
            [{"name": total_cat} for total_cat in df_long["大總類"].unique()] +
            [{"name": group} for group in df["組別"].unique()] +
            [{"name": sub_cat} for sub_cat in df_long["小總類"].unique()] +
            [{"name": name} for name in df["姓名"].unique()]
        )
        
        # 建立連結
        links = (
            [{"source": row["大總類"], "target": row["組別"], "value": row["value"]} for _, row in group_agg.iterrows()] +
            [{"source": row["組別"], "target": row["小總類"], "value": row["value"]} for _, row in group_sub_agg.iterrows()] +
            [{"source": row["小總類"], "target": row["姓名"], "value": row["value"]} for _, row in df_long.iterrows()]
        )
        
        sankey = (
            Sankey()
            .add(
                "Sankey Diagram",
                nodes=nodes,
                links=links,
                linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
                label_opts=opts.LabelOpts(position="right"),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="Sankey 圖表"),
                toolbox_opts=opts.ToolboxOpts(),
                legend_opts=opts.LegendOpts(),
            )
        )
        #st.write("Links:", links)

        st_pyecharts(sankey, height="400px")
st.markdown("""
    <div class="footer">
        有問題請聯絡: <a href="mailto:pineapple168.mg11@nycu.edu.tw">cphsiao-20250201</a>
    </div>
""", unsafe_allow_html=True)