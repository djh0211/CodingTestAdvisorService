import streamlit as st
import requests
from PIL import Image
import tools
import pandas as pd
import time
import sys
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import itertools
from datetime import datetime
import altair as alt
from datetime import date, timedelta
import json
from collections import defaultdict


from google.cloud import spanner



# application setting
st.set_page_config(
    page_title="코딩테스트 어드바이저",
    page_icon="👾",
    layout="wide",
    initial_sidebar_state="expanded",
    ) 

# Pages logic 
if 'page' not in st.session_state: st.session_state.page = "login"


def goto_login_Page():
    # TODO 나머지
    st.session_state.page="login"
    if "user_id" in st.session_state:
        del st.session_state["user_id"]
    if "user_data_dic" in st.session_state:
        del st.session_state["user_data_dic"]
    if "user_history_df" in st.session_state:
        del st.session_state["user_history_df"]
    if "selected_test_info" in st.session_state:
        del st.session_state["selected_test_info"]
    if "questions_info_in_test" in st.session_state:
        del st.session_state["questions_info_in_test"]
    if "questions_tags_in_test" in st.session_state:
        del st.session_state["questions_tags_in_test"]
    if "questions_tags_in_review" in st.session_state:
        del st.session_state["questions_tags_in_review"]
    if "questions_tags_in_preview" in st.session_state:
        del st.session_state["questions_tags_in_preview"]
    if "recommendation" in st.session_state:
        del st.session_state["recommendation"]
    if "chart_data" in st.session_state:
        del st.session_state["chart_data"]
    if "period_data_dic" in st.session_state:
        del st.session_state["period_data_dic"]
    if "preview_recommendation_tags_name_list" in st.session_state:
        del st.session_state["preview_recommendation_tags_name_list"]
    if "review_recommendation_tags_name_list" in st.session_state:
        del st.session_state["review_recommendation_tags_name_list"]
    st.experimental_rerun()
    
def goto_main_Page():
    st.session_state.page ="main"
    st.experimental_rerun()
    


# Spanner setting
spanner_client = spanner.Client()
instance = spanner_client.instance("***")
database = instance.database("***")

ph = st.empty()

## login_Page
if st.session_state.page == "login":
    with ph.container():
        st.markdown("<h1 style='text-align: center;'>코딩테스트 어드바이저 서비스</h1>", unsafe_allow_html=True)
        with st.form("백준 아이디를 입력해주세요.") as a:
            user_id= st.text_input("백준아이디")
            submitted = st.form_submit_button("로그인")
            if submitted: #로그인 버튼 누르면 아이디 유효성 검사 진행
                res= tools.id_check(user_id)
                if res==-2: #공백 포함 다시입력
                    st.error("입력값에 공백이 포함되어있습니다. 다시 입력 바랍니다.")
                elif res==-1:
                    st.error("올바르지 않은 백준 아이디입니다 다시 입력 바랍니다.")
                else: 
                    res=tools.is_user_in_baekjoon(user_id)
                    #백준에 있으면 1 없으면 0 오류나면 -1
                    if res==1:
                        # st.write(f"{user_id} 는 존재합니다.")
                        st.session_state["user_id"]=user_id
                        user_id= st.session_state["user_id"]
                        # 우리 서비스 기존 사용자인지 신규인지 검사
                        res=tools.is_user_in_spanner(user_id,database)
                        if res: #user에 아이디 존재하네?
                            res= tools.is_user_registered(user_id,database)
                            if res: #이미 등록되어있는 유저네?
                                # TODO: DB에서 모든걸 가져와
                                st.success("기존 이용자 입니다.")
                                user_data_dic= tools.get_user_data_from_spanner(user_id,database)
                                user_history_df= tools.get_history_from_spanner(user_id,database)
                                
                                if user_data_dic==False or user_history_df==False:
                                    st.error("유저 정보 혹은 학습기록을 갖고 오는데 실패했습니다. 아이디를 다시 입력해주세요.")
                                else:
                                    st.success("정보 불러오기 완료.")
                                    user_history_df=tools.history_list_to_df(user_history_df)
                                    time_diff= user_history_df.submitted_epochtime.diff()
                                    user_history_df['submitted_epochtime']=np.where(time_diff.isna(),0,time_diff).astype('int')
                                    
                                    st.session_state["user_data_dic"]=user_data_dic
                                    st.session_state["user_history_df"]=user_history_df
                                    goto_main_Page()
                            else: # DB에서 기록 + 백준 추가기록 + .....
                                full_df=tools.get_additional_history_from_baekjoon(user_id,database)
                                
                                if full_df.empty == False:
                                    full=tools.preprocess_history_data_to_insert_spanner(full_df)
                                    res=tools.insert_history_data_to_spanner(database,data=full)
                                    if res==-1:
                                        st.error("학습기록 최신화에 실패하였습니다. 로그인을 다시 해주세요.")
                                    else:
                                        res=tools.control_update_user_data_all(database,user_id)
                                        st.success("데이터 업데이트 확인")
                                        user_data_dic= tools.get_user_data_from_spanner(user_id,database)
                                        user_history_df= tools.get_history_from_spanner(user_id,database)
                                        if user_data_dic==False or user_history_df==False:
                                            st.error("유저 정보 혹은 학습 기록을 갖고 오는데 실패했습니다. 아이디를 다시 입력해주세요.")
                                        else: 
                                            user_history_df=tools.history_list_to_df(user_history_df)
                                            time_diff= user_history_df.submitted_epochtime.diff()
                                            user_history_df['submitted_epochtime']=np.where(time_diff.isna(),0,time_diff).astype('int')
                                            
                                            st.session_state["user_data_dic"]=user_data_dic
                                            st.session_state["user_history_df"]=user_history_df
                                                                                               
                                            st.success("정보 불러오기 완료.")
                                            
                                            goto_main_Page()
                                        
                                        
                                else:
                                    # TODO 임시함수
                                    res=database.run_in_transaction(tools.update_registered_value,
                                                                    user_id=user_id,
                                                                    registered_value=True)
                                    if res==-1:
                                        st.error("유저 registered update 에러")
                                    else:
                                        st.success("유저 등록 확인")
                                        user_data_dic= tools.get_user_data_from_spanner(user_id,database)
                                        user_history_df= tools.get_history_from_spanner(user_id,database)
                                        if user_data_dic==False or user_history_df==False:
                                            st.error("유저 정보 혹은 학습 기록을 갖고 오는데 실패했습니다. 아이디를 다시 입력해주세요.")
                                        else: 
                                            user_history_df=tools.history_list_to_df(user_history_df)
                                            time_diff= user_history_df.submitted_epochtime.diff()
                                            user_history_df['submitted_epochtime']=np.where(time_diff.isna(),0,time_diff).astype('int')
                                            
                                            st.session_state["user_data_dic"]=user_data_dic
                                            st.session_state["user_history_df"]=user_history_df
                                                                                               
                                            st.success("정보 불러오기 완료.")
                                            
                                            goto_main_Page()
                                        
                        else: #user에 아이디 없네? 기록도 없겠네
                            st.success("신규유저입니다.\n학습기록과 추천,통계정보를 불러오는 중입니다...")
                            user_history_df= tools.get_full_history_from_baekjoon(user_id)

                            if user_history_df.empty == True: #받아오는데 오류난거
                                st.error("오류! 다시 시도 해주세요.")
                            else:
                                user_history= tools.preprocess_history_data_to_insert_spanner(user_history_df)
                                res= tools.insert_history_data_to_spanner(database,user_history)
                                if res==-1:
                                    st.error("학습기록 insert 실패")
                                else:
                                    st.success("학습 기록을 성공적으로 받았습니다. 유저 등록하겠습니다!")
                                    res=tools.insert_user_data_to_spanner(database,user_id)
                                    if res==-1:
                                        st.error("error 실패")
                                    elif res==-2:
                                        st.error("solved.ac 미등록 유저입니다!")
                                    else:
                                        user_data_dic= tools.get_user_data_from_spanner(user_id,database)
                                        user_history_df= tools.get_history_from_spanner(user_id,database)
                                        if user_data_dic==False or user_history_df==False:
                                            st.error("유저 정보 혹은 학습 기록을 갖고 오는데 실패했습니다. 아이디를 다시 입력해주세요.")
                                        else: 
                                            user_history_df=tools.history_list_to_df(user_history_df)
                                            time_diff= user_history_df.submitted_epochtime.diff()
                                            user_history_df['submitted_epochtime']=np.where(time_diff.isna(),0,time_diff).astype('int')
                                            
                                            st.session_state["user_data_dic"]=user_data_dic
                                            st.session_state["user_history_df"]=user_history_df
                                                                                               
                                            st.success("정보 불러오기 완료.")
                                            
                                            goto_main_Page()
                                        
                    elif res==0:
                        st.error(f"{user_id} 는 존재하지 않거나 아직 문제를 하나도 풀지 않았습니다. 다시 입력해주세요.")
                    else:
                        st.error("요청 오류 다시 시도 해주세요.")
                        
        banner_container=st.container()
        with banner_container:
            banner_image = Image.open('banner.jpg')
            st.image(banner_image,use_column_width=True)
            


                                                    
## main_Page
elif st.session_state.page == "main":
    with ph.container():
        with st.spinner(""):
            if "user_id" in st.session_state: user_id=st.session_state["user_id"]
            if "user_data_dic" in st.session_state: user_data_dic= st.session_state["user_data_dic"]
            if "user_history_df" in st.session_state:
                user_history_df=st.session_state["user_history_df"]
            if "period_data_dic" not in st.session_state:
                level_distribution,level_name_ll,level_cnt_ll= tools.get_my_level_distribution_stats(database,user_id)
                tag_distribution=tools.get_my_tag_distribution_stats(database,user_id)
                temp_dic={}
                temp_dic["level_distribution"]=level_distribution
                temp_dic["level_name_ll"]=level_name_ll
                temp_dic["level_cnt_ll"]=level_cnt_ll
                temp_dic["tag_distribution"]=tag_distribution
                st.session_state["period_data_dic"]={}
                st.session_state["period_data_dic"]["전체 기간"]=temp_dic
                    
                level_distribution,level_name_ll,level_cnt_ll= tools.get_my_level_distribution_stats_per_period(database,user_id,7)
                tag_distribution=tools.get_my_tag_distribution_stats_per_period(database,user_id,7)
                temp_dic={}
                temp_dic["level_distribution"]=level_distribution
                temp_dic["level_name_ll"]=level_name_ll
                temp_dic["level_cnt_ll"]=level_cnt_ll
                temp_dic["tag_distribution"]=tag_distribution
                st.session_state["period_data_dic"]["최근 1주"]=temp_dic
                
                level_distribution,level_name_ll,level_cnt_ll= tools.get_my_level_distribution_stats_per_period(database,user_id,30)
                tag_distribution=tools.get_my_tag_distribution_stats_per_period(database,user_id,30)
                temp_dic={}
                temp_dic["level_distribution"]=level_distribution
                temp_dic["level_name_ll"]=level_name_ll
                temp_dic["level_cnt_ll"]=level_cnt_ll
                temp_dic["tag_distribution"]=tag_distribution
                st.session_state["period_data_dic"]["최근 1달"]=temp_dic
                
                level_distribution,level_name_ll,level_cnt_ll= tools.get_my_level_distribution_stats_per_period(database,user_id,365)
                tag_distribution=tools.get_my_tag_distribution_stats_per_period(database,user_id,365)
                temp_dic={}
                temp_dic["level_distribution"]=level_distribution
                temp_dic["level_name_ll"]=level_name_ll
                temp_dic["level_cnt_ll"]=level_cnt_ll
                temp_dic["tag_distribution"]=tag_distribution
                st.session_state["period_data_dic"]["최근 1년"]=temp_dic
                level_distribution,level_name_ll,level_cnt_ll,tag_distribution=(st.session_state["period_data_dic"]["전체 기간"]["level_distribution"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["level_name_ll"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["level_cnt_ll"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["tag_distribution"])
            else:
                level_distribution,level_name_ll,level_cnt_ll,tag_distribution=(st.session_state["period_data_dic"]["전체 기간"]["level_distribution"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["level_name_ll"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["level_cnt_ll"],
                                                                                st.session_state["period_data_dic"]["전체 기간"]["tag_distribution"])
            if "chart_data" not in st.session_state:
                st.session_state["chart_data"]={}
                st.session_state["chart_data"]["주 단위"]=tools.get_statistics_graph_per_week(database,user_id)
                st.session_state["chart_data"]["월 단위"]=tools.get_statistics_graph_per_month(database,user_id)
                st.session_state["chart_data"]["년 단위"]=tools.get_statistics_graph_per_year(database,user_id)
                chart_data=st.session_state["chart_data"]["주 단위"]
            else:
                chart_data=st.session_state["chart_data"]["주 단위"]
            if "recommendation" not in st.session_state:
                data_dic={}
                data_dic["problem_ids"]=user_history_df.question_id.tolist()
                tmp_c=user_history_df.result.tolist()
                
                data_dic["problem_results"]=list(map(tools.get_binary_result,tmp_c))
                data_dic["problem_time_diffs"]=user_history_df.submitted_epochtime.tolist()
                
                q_list=tools.get_sample_q100()
                params_get_recommendation={}
                param_types_get_recommendation={}
                for i in range(len(q_list)):
                    params_get_recommendation[f"q{i}"]=q_list[i]
                    param_types_get_recommendation[f"q{i}"]= spanner.param_types.INT64
                sql_get_recommendation_info="WITH tmp AS (SELECT * FROM question WHERE id in "
                sql_get_recommendation_info+='('+','.join([f"@q{i}" for i in range(len(q_list))])+')) '
                sql_get_recommendation_info+="SELECT A.id,title,name,level_id FROM tmp A LEFT JOIN level B ON A.level_id=B.id"
                with database.snapshot() as snapshot:
                    recommendation = snapshot.execute_sql(
                        sql_get_recommendation_info,
                        params=params_get_recommendation,
                        param_types=param_types_get_recommendation
                    )
                recommendation=list(iter(recommendation))
                my_unique_questions=set(data_dic["problem_ids"])
                recommendation_type=[]
                for i in list(map(lambda x:x[0],recommendation)):
                    if i in my_unique_questions:
                        recommendation_type.append(["복습"])
                    else:
                        recommendation_type.append(["예습"])
                recommendation=np.concatenate([recommendation, recommendation_type], 1)
                te1={}
                te2={}
                for i in recommendation:
                    if i[-1]=="복습":
                        te1[i[0]]=i[1:]
                    else:
                        te2[i[0]]=i[1:]

                recommendation={}
                recommendation["복습"]=te1
                recommendation["예습"]=te2
                st.session_state["recommendation"]=recommendation
                
                # TODO 일단 10개나오는 api는 주석 start
            #     url = "********"
            #     headers = {"Accept": "application/json"}

            #     response = requests.post(url, json=data_dic, headers=headers)
            #     q_list=json.loads(response.json()["recommended_problem_ids"])
            # #             print(sorted(q_list))
            #     # TODO 만약 10개가 아니라 개수 지정해서 문제 갖고 올 수 있으면 수정 필요
            #     params_get_recommendation={}
            #     param_types_get_recommendation={}
            #     for i in range(10):
            #         params_get_recommendation[f"q{i}"]=q_list[i]
            #         param_types_get_recommendation[f"q{i}"]= spanner.param_types.INT64
            #     with database.snapshot() as snapshot:
            #         recommendation = snapshot.execute_sql(
            #             "WITH tmp AS (SELECT * FROM question WHERE id in (@q0,@q1,@q2,@q3,@q4,@q5,@q6,@q7,@q8,@q9))"
            #             "SELECT A.id,title,name,level_id FROM tmp A LEFT JOIN level B ON A.level_id=B.id",
            #             params=params_get_recommendation,
            #             param_types=param_types_get_recommendation
            #         )
            #     recommendation=list(iter(recommendation))
            #     my_unique_questions=set(data_dic["problem_ids"])
            #     recommendation_type=[]
            #     for i in list(map(lambda x:x[0],recommendation)):
            #         if i in my_unique_questions:
            #             recommendation_type.append(["복습"])
            #         else:
            #             recommendation_type.append(["예습"])
            #     recommendation=np.concatenate([recommendation, recommendation_type], 1)
            #     te1=[]
            #     te2=[]
            #     for i in recommendation:
            #         if i[-1]=="복습":
            #             te1.append(i)
            #         else:
            #             te2.append(i)
            #     recommendation={}
            #     recommendation["복습"]=te1
            #     recommendation["예습"]=te2
            #     st.session_state["recommendation"]=recommendation
                # TODO 일단 10개나오는 api는 주석 end
            else:
                recommendation=st.session_state["recommendation"]
                
                
            if "tags_name_list" not in st.session_state:
                with database.snapshot() as snapshot:
                    tags_name_list = snapshot.execute_sql(
                        "SELECT ko_name FROM tag"
                    )
                tags_name_list=list(iter(tags_name_list))
                tags_name_list=list(itertools.chain.from_iterable(tags_name_list))
                st.session_state["tags_name_list"]=tags_name_list
            else:
                tags_name_list=st.session_state["tags_name_list"] 
   
        
        mpl.rcParams['font.size'] = 9.0
        m = st.markdown("""<style>
                            .button {
                                background-color: #4CAF50; /* Green */
                                border: none;
                                border-radius: 12px;
                                color: white;
                                padding: 9px 18px;
                                text-align: center;
                                text-decoration: none;
                                display: inline-block;
                                font-size: 16px;
                                margin: 4px 2px;
                                cursor: pointer;
                                }
                            </style>""", unsafe_allow_html=True)
        
        t1,t2= st.columns([6,1])
        with t2:
            btn_logout= st.button("로그아웃")
            if btn_logout:
                goto_login_Page()
        container1= st.container()
        with container1:
            t11,t12=st.columns([20,1],gap="small")
            with t11:
                # st.write(user_data_dic)
                my_level_name=tools.level_id_to_level_name_from_spanner(database,user_data_dic["level_id"])
                title_str=f'<p><span style="font-size: 40px"><b>{user_id} </b></span><span style="font-size:17px; color:{tools.level_to_colorcode(user_data_dic["level_id"])}">{my_level_name}</span></p>'
                st.markdown(title_str,unsafe_allow_html=True)
            with t12:
                # TODO action 만들기
                btn_refresh= st.button("🔁")
                if btn_refresh:
                    with st.spinner(" "):
                        full_df=tools.get_additional_history_from_baekjoon(user_id,database)
                        if full_df.empty == False:
                            full=tools.preprocess_history_data_to_insert_spanner(full_df)
                            res=tools.insert_history_data_to_spanner(database,data=full)
                            
                            if res==-1:
                                st.error("학습기록 최신화에 실패하였습니다. 버튼을 다시 눌러주세요.")
                       
                        res=tools.control_update_user_data_all(database,user_id)
                        user_data_dic= tools.get_user_data_from_spanner(user_id,database)
                        user_history_df= tools.get_history_from_spanner(user_id,database)
                        if user_data_dic==False or user_history_df==False:
                            st.error("유저 정보 혹은 학습 기록을 갖고 오는데 실패했습니다. 버튼을 다시 눌러주세요.")
                        else: 
                            user_history_df=tools.history_list_to_df(user_history_df)
                            time_diff= user_history_df.submitted_epochtime.diff()
                            user_history_df['submitted_epochtime']=np.where(time_diff.isna(),0,time_diff).astype('int')
                            
                            st.session_state["user_data_dic"]=user_data_dic
                            st.session_state["user_history_df"]=user_history_df
                            if "selected_test_info" in st.session_state:
                                del st.session_state["selected_test_info"]
                            if "questions_info_in_test" in st.session_state:
                                del st.session_state["questions_info_in_test"]
                            if "questions_tags_in_test" in st.session_state:
                                del st.session_state["questions_tags_in_test"]
                            if "questions_tags_in_review" in st.session_state:
                                del st.session_state["questions_tags_in_review"]
                            if "questions_tags_in_preview" in st.session_state:
                                del st.session_state["questions_tags_in_preview"]
                            if "recommendation" in st.session_state:
                                del st.session_state["recommendation"]
                            if "chart_data" in st.session_state:
                                del st.session_state["chart_data"]
                            if "period_data_dic" in st.session_state:
                                del st.session_state["period_data_dic"]
                            if "review_recommendation_tags_name_list" in st.session_state:
                                del st.session_state["review_recommendation_tags_name_list"]
                            if "preview_recommendation_tags_name_list" in st.session_state:
                                del st.session_state["preview_recommendation_tags_name_list"]
                            
                            st.experimental_rerun()


        # st.write(st.session_state)
        tab1, tab2, tab3, tab4= st.tabs(["사용자 통계","코딩 테스트 합격률 예측",
                                         "복습 문제 추천","예습 문제 추천"])
        with tab1:
            container2= st.container()
            with container2:
                c111,c112= st.columns([2,11],gap="small")
                with c111:
                    selectbox1=st.selectbox(" ",["전체 기간","최근 1주","최근 1달","최근 1년"])
                st.caption("난이도 분포")
                col1, col2 = st.columns([2,3],gap="large")
                level_distribution,level_name_ll,level_cnt_ll,tag_distribution=(st.session_state["period_data_dic"][selectbox1]["level_distribution"],
                                                                        st.session_state["period_data_dic"][selectbox1]["level_name_ll"],
                                                                        st.session_state["period_data_dic"][selectbox1]["level_cnt_ll"],
                                                                        st.session_state["period_data_dic"][selectbox1]["tag_distribution"])
                
                with col1: 
                    newdic={}
                    newdic["etc"]=0       
                    if sum(level_cnt_ll)==0:
                        wedgeprops={'width': 0.75, 'edgecolor': 'w', 'linewidth': 0}
                        fig1, ax1 = plt.subplots()
                        # colors=colors
                        ax1.pie([100], labels=["No learning history"],autopct='%.1f%%',
                                startangle=90, counterclock=False, wedgeprops=wedgeprops,
                                pctdistance=0.75, labeldistance=1.2)
                        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                        st.pyplot(fig1)
                    else:
                        for key in list(level_distribution.keys()):
                            if level_distribution[key]/sum(level_cnt_ll)<0.03:
                                newdic["etc"] += level_distribution[key]
                            else:
                                newdic[key]=level_distribution[key]

                        ratio = newdic.values()
                        labels = newdic.keys()
                        pallete=tools.get_piechart_colors()
                        piechart_colors=[]
                        dic_level_name_to_level_id= tools.get_dic_level_name_to_level_id(database)

                        for i in labels:
                            if i=="etc":
                                piechart_colors.append(pallete[0])
                            else:
                                tgt=dic_level_name_to_level_id[i]
                                piechart_colors.append(pallete[tgt])


                        wedgeprops={'width': 0.75, 'edgecolor': 'w', 'linewidth': 0}
                        fig1, ax1 = plt.subplots()
                        # colors=colors
                        ax1.pie(ratio, labels=labels,colors=piechart_colors,autopct='%.1f%%',
                                startangle=90, counterclock=False, wedgeprops=wedgeprops,
                                pctdistance=0.75, labeldistance=1.2)

                        
                        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                        st.pyplot(fig1)
                
                with col2:
                    if sum(level_cnt_ll)==0:
                        st.info("기간 내 풀은 문제가 없습니다.")
                    else:
                        level_cnt_df = pd.DataFrame(columns=(['레벨', '문제', '']))
                        level_cnt_df["레벨"]=["Bronze","Silver","Gold","Platinum","Diamond","Ruby"]
                        level_range_cnt_ll=[sum(level_cnt_ll[:5]),sum(level_cnt_ll[5:10]),sum(level_cnt_ll[10:15]),
                                            sum(level_cnt_ll[15:20]),sum(level_cnt_ll[20:25]),sum(level_cnt_ll[25:30])]
                        level_cnt_df["문제"]=level_range_cnt_ll
                        def f1(x):
                            x= 100*round(x/sum(level_range_cnt_ll),3)
                            
                            return "{:.1f}%".format(x)
                        level_cnt_df[""]=list(map(f1,level_range_cnt_ll))

                        # CSS to inject contained in a string
                        hide_table_row_index = """
                                    <style>
                                    thead tr th:first-child {display:none}
                                    tbody th {display:none}
                                    </style>
                                    """

                        # Inject CSS with Markdown
                        st.markdown(hide_table_row_index, unsafe_allow_html=True)

                        # Display a static table
                        st.table(level_cnt_df)
                        
                        
                    

            container3= st.container()
            if tag_distribution:
                with container3:
                    st.caption("태그 분포")
                    
                    tag_name_ll=list(map(lambda x:x[1],tag_distribution))
                    tag_cnt_ll=list(map(lambda x:x[2],tag_distribution))

                    
                    
                    tag_cnt_df = pd.DataFrame(columns=(['태그', '문제','']))
                    tag_cnt_df["태그"]=list(map(lambda x:"#{0}".format(x),tag_name_ll))
                    tag_cnt_df["문제"]=tag_cnt_ll
                    
                    def f2(x):
                            x= 100*round(x/sum(tag_cnt_ll),3)
                            
                            return "{:.1f}%".format(x)
                    tag_cnt_df['']=list(map(f2,tag_cnt_ll))
                    
                    hide_table_row_index = """
                                        <style>
                                        thead tr th:first-child {display:none}
                                        tbody th {display:none}
                                        </style>
                                        """

                    st.markdown(hide_table_row_index, unsafe_allow_html=True)

                        # Display a static table
                    st.table(tag_cnt_df[:11])
            
            container6= st.container()
            with container6:
                st.caption("학습이력 그래프")
                col61,col62=st.columns([2,8])
                with col61:
                    radio_btn=st.radio("options",('주 단위', '월 단위', '년 단위'))
                with col62:
                    chart_data=st.session_state["chart_data"][radio_btn]
                    st.line_chart(chart_data)
                    
                        
        with tab2:
            test_selectbox1=None
            test_selectbox2=None
            test_selectbox3=None
            
            test_container=st.container()
            with test_container:
                test_col1,test_col2= st.columns([3,9],gap="medium")
                with test_col1:
                    with database.snapshot() as snapshot:
                            test_selectbox1_ll = snapshot.execute_sql(
                                "SELECT major_category_name FROM test GROUP BY 1,major_category_id ORDER BY major_category_id"
                            )
                            
                    test_selectbox1_ll=["==대분류=="]+list(itertools.chain(*list(iter(test_selectbox1_ll))))
                    test_selectbox1=st.selectbox("코딩테스트를 선택해주세요.",test_selectbox1_ll)
                    if test_selectbox1!="==대분류==":
                        with database.snapshot() as snapshot:
                            test_selectbox2_ll = snapshot.execute_sql(
                                "SELECT middle_category_name FROM test WHERE major_category_name=@major_name GROUP BY 1,middle_category_id ORDER BY middle_category_id",
                                params={"major_name":test_selectbox1},
                                param_types={"major_name": spanner.param_types.STRING}
                                
                            )
                        test_selectbox2_ll=["==중분류=="]+list(itertools.chain(*list(iter(test_selectbox2_ll))))
                        test_selectbox2=st.selectbox("",test_selectbox2_ll)
                        if test_selectbox1!="==중분류==":
                            with database.snapshot() as snapshot:
                                test_selectbox3_ll = snapshot.execute_sql(
                                    "SELECT sub_category_name FROM test WHERE major_category_name=@major_name AND middle_category_name=@middle_name GROUP BY 1,sub_category_id ORDER BY sub_category_id",
                                    params={"major_name":test_selectbox1,
                                            "middle_name":test_selectbox2},
                                    param_types={"major_name": spanner.param_types.STRING,
                                                "middle_name": spanner.param_types.STRING}
                                    
                                )
                            test_selectbox3_ll=["==소분류=="]+list(itertools.chain(*list(iter(test_selectbox3_ll))))
                            if test_selectbox3_ll!=["==소분류==",None]:
                                test_selectbox3=st.selectbox("",test_selectbox3_ll)
                    apply_btn_col1,apply_btn_col2=st.columns([9,4])
                    with apply_btn_col2:
                        test_apply_btn=st.button("적용",key="test_apply_btn")

                    
                    
                with test_col2:
                    if test_apply_btn:
                        if test_selectbox1 and test_selectbox2:
                            if test_selectbox3!=None:
                                with database.snapshot() as snapshot:
                                    selected_test_info_t = snapshot.execute_sql(
                                        "SELECT id,major_category_name,middle_category_name,sub_category_name FROM test WHERE major_category_name=@major_name AND middle_category_name=@middle_name AND sub_category_name=@sub_name",
                                        params={"major_name":test_selectbox1,
                                                "middle_name":test_selectbox2,
                                                "sub_name":test_selectbox3},
                                        param_types={"major_name": spanner.param_types.STRING,
                                                    "middle_name": spanner.param_types.STRING,
                                                    "sub_name": spanner.param_types.STRING}
                                    )
                                    selected_test_info_t=list(iter(selected_test_info_t))[0]
                                    selected_test_info={}
                                    if selected_test_info_t!=[]:
                                        selected_test_info["id"]=selected_test_info_t[0]
                                        selected_test_info["major_category_name"]=selected_test_info_t[1]
                                        selected_test_info["middle_category_name"]=selected_test_info_t[2]
                                        selected_test_info["sub_category_name"]=selected_test_info_t[3]
                                        with database.snapshot() as snapshot:
                                            questions_in_test = snapshot.execute_sql(
                                                "SELECT * FROM test_question_relation WHERE test_id=@testid",
                                                params={"testid":selected_test_info['id'],
                                                        },
                                                param_types={"testid": spanner.param_types.INT64,
                                                            }
                                            )
                                        questions_in_test=list(map(lambda x:x[1],list(iter(questions_in_test))))
                                        selected_test_info["questions_in_test"]=questions_in_test
                                        st.session_state.selected_test_info=selected_test_info
                                        if "questions_info_in_test" in st.session_state:
                                            del st.session_state["questions_info_in_test"]
                                        if "questions_tags_in_test" in st.session_state:
                                            del st.session_state["questions_tags_in_test"]
                                    else:
                                        st.warning("코딩테스트 선택을 완료해주세요.")
                            else:
                                with database.snapshot() as snapshot:
                                    selected_test_info_t = snapshot.execute_sql(
                                        "SELECT id,major_category_name,middle_category_name,sub_category_name FROM test WHERE major_category_name=@major_name AND middle_category_name=@middle_name",
                                        params={"major_name":test_selectbox1,
                                                "middle_name":test_selectbox2,
                                                },
                                        param_types={"major_name": spanner.param_types.STRING,
                                                    "middle_name": spanner.param_types.STRING,
                                                    }
                                    )
                                    selected_test_info_t=list(iter(selected_test_info_t))[0]
                                    selected_test_info={}
                                    if selected_test_info_t!=[]:
                                        selected_test_info["id"]=selected_test_info_t[0]
                                        selected_test_info["major_category_name"]=selected_test_info_t[1]
                                        selected_test_info["middle_category_name"]=selected_test_info_t[2]
                                        selected_test_info["sub_category_name"]=selected_test_info_t[3]
                                        with database.snapshot() as snapshot:
                                            questions_in_test = snapshot.execute_sql(
                                                "SELECT * FROM test_question_relation WHERE test_id=@testid",
                                                params={"testid":selected_test_info['id'],
                                                        },
                                                param_types={"testid": spanner.param_types.INT64,
                                                            }
                                            )
                                        questions_in_test=list(map(lambda x:x[1],list(iter(questions_in_test))))
                                        selected_test_info["questions_in_test"]=questions_in_test
                                        st.session_state.selected_test_info=selected_test_info
                                        if "questions_info_in_test" in st.session_state:
                                            del st.session_state["questions_info_in_test"]
                                        if "questions_tags_in_test" in st.session_state:
                                            del st.session_state["questions_tags_in_test"]
                                    else:
                                        st.warning("코딩테스트 선택을 완료해주세요.")
                                        
                    if "selected_test_info" in st.session_state:
                        selected_test_info=st.session_state.selected_test_info
                        if selected_test_info["sub_category_name"]==None:
                            selected_test_title=f'<p><span style="font-size: 35px;"><b>{selected_test_info["major_category_name"]}&nbsp;&nbsp;</b></span><span style="font-size:20px;color:#e09e37"><b>{selected_test_info["middle_category_name"]}</b></span></p>'
                        else:
                            selected_test_title=f'<p><span style="font-size: 35px;"><b>{selected_test_info["major_category_name"]}<br></b></span><span style="font-size:24px;color:#e09e37"><b>{selected_test_info["middle_category_name"]}&nbsp;&nbsp;</b></span><span style="font-size:19px;color:#ea3364"><b>{selected_test_info["sub_category_name"]}</b></span></p>'
                        st.markdown(selected_test_title, unsafe_allow_html=True)
                        

                        if "questions_info_in_test" not in st.session_state:
                            sql_get_questions_info="WITH tmp AS (SELECT * FROM question WHERE id in "
                            sql_get_questions_info+='('+','.join([f"@q{i}" for i in range(len(selected_test_info["questions_in_test"]))])+')) '
                            sql_get_questions_info+="SELECT A.id,title,name,level_id FROM tmp A LEFT JOIN level B ON A.level_id=B.id"
                            params_get_questions_info={}
                            for i in range(len(selected_test_info["questions_in_test"])):
                                params_get_questions_info[f"q{i}"]=selected_test_info["questions_in_test"][i]
                            params_types_get_questions_info={}
                            for i in range(len(selected_test_info["questions_in_test"])):
                                params_types_get_questions_info[f"q{i}"]=spanner.param_types.INT64

                            with database.snapshot() as snapshot:
                                result_get_questions_info= snapshot.execute_sql(
                                    sql_get_questions_info,
                                    params=params_get_questions_info,
                                    param_types=params_types_get_questions_info
                                )
                            result_get_questions_info=list(iter(result_get_questions_info))
                            questions_info_in_test={}
                            questions_tags_in_test={}
                            for i in result_get_questions_info:
                                questions_info_in_test[i[0]]=i[1:]
                            for i in result_get_questions_info:
                                with database.snapshot() as snapshot:
                                    questions_tags_in_test[i[0]]=tools.get_question_tags_from_spanner(database,i[0])
                            st.session_state.questions_info_in_test=questions_info_in_test
                            st.session_state.questions_tags_in_test=questions_tags_in_test
                        else:
                            questions_info_in_test=st.session_state["questions_info_in_test"]
                            questions_tags_in_test=st.session_state["questions_tags_in_test"]
                            
                        
                        test_questions_container_list=[]
                        for i in range(len(selected_test_info["questions_in_test"])):
                            test_questions_container_list.append(st.container())
                        for i in range(len(test_questions_container_list)):
                            question_id=selected_test_info["questions_in_test"][i]
                            question_name=questions_info_in_test[question_id][0]
                            level_id=questions_info_in_test[question_id][2]
                            level_name=questions_info_in_test[question_id][1]
                            with test_questions_container_list[i]:
                                test_questions_tags=questions_tags_in_test[question_id]
                                with st.expander(f"**:green[# {question_id}]**       **{question_name}**",expanded=True):
                                    ts=""
                                    if len(test_questions_tags)!=0:
                                        for i in range(len(test_questions_tags)):
                                            ts=ts+"#"+str(test_questions_tags[i])+"&nbsp;"
                                    tag = f'<p><span style="font-size: 13px; color: {tools.level_to_colorcode(level_id)}"><b>{level_name}&nbsp;</b></span><span style="font-size: 10px">{ts}</span></p>'
                                    st.markdown(tag, unsafe_allow_html=True)
                                    
                                    st.markdown(f'<p><span style="font-size: 13px; color: #ea3364"><b>예상정답률:&nbsp;</b></span><span style="font-size: 13px; color: #ea3364"><b>90%</b></span></p',unsafe_allow_html=True)
                                    
                                    question_url = f"https://www.acmicpc.net/problem/{question_id}"
                                    st.markdown(f'''
                                        <a href={question_url}><button class="button button1">백준에서 보기</button></a>
                                        ''',
                                        unsafe_allow_html=True)
                                    
                        
   

        with tab3:
            container4= st.container()
            with container4:
                review_recommendation=recommendation["복습"]
                if len(review_recommendation)!=0:
                    if "questions_tags_in_review" not in st.session_state:
                        params_get_recommendation_tags={}
                        param_types_get_recommendation_tags={}
                        for i, (key, value) in enumerate(review_recommendation.items()):
                            params_get_recommendation_tags[f"q{i}"]=key
                            param_types_get_recommendation_tags[f"q{i}"]= spanner.param_types.INT64

                        sql_get_recommendation_tags="SELECT question_id,ko_name tag_name FROM question_tag_relation A, tag B WHERE A.question_id in "
                        sql_get_recommendation_tags+='('+','.join([f"@q{i}" for i in range(len(review_recommendation))])+') '
                        sql_get_recommendation_tags+="AND A.tag_id=B.id"
                        with database.snapshot() as snapshot:
                            result_get_recommendation_tags= snapshot.execute_sql(
                                sql_get_recommendation_tags,
                                params=params_get_recommendation_tags,
                                param_types=param_types_get_recommendation_tags
                            )
                        result_get_recommendation_tags=list(iter(result_get_recommendation_tags))
                        tsts=defaultdict(list)
                        for i in result_get_recommendation_tags:
                            tsts[i[0]].append(i[1])
                        st.session_state["questions_tags_in_review"]=tsts
                        questions_tags_in_review=st.session_state["questions_tags_in_review"]
                    else:
                        questions_tags_in_review=st.session_state["questions_tags_in_review"]
                c41,c42= st.columns([3,9])
                with c41:
                    if "review_recommendation_tags_name_list" not in st.session_state:
                        review_recommendation_tags_name_list=list(set(itertools.chain.from_iterable(questions_tags_in_review.values())))
                        st.session_state["review_recommendation_tags_name_list"]=review_recommendation_tags_name_list
                    else:
                        review_recommendation_tags_name_list=st.session_state["review_recommendation_tags_name_list"]
                    recommendation_multiselect1 = st.multiselect(
                        '큐레이션을 원하는 태그들을 선택해주세요 :)',
                        review_recommendation_tags_name_list,[],max_selections=5,key="recommendation_multiselect1")
                    st.info("1개 이상 5개 이하의 태그를 선택해주세요.")
                with c42:
                    # TODO 만약 100개 들어온다면 페이지 기능 추가 / questions_tags_in_review 이거 하나씩 스패너에 요청하지 말고 한꺼번에 in 걸어서 받고 그 안에서 검색하는 식으로 하자 
                        if not recommendation_multiselect1:
                            pcol1,pcol2=st.columns([4,1])
                            with pcol2:
                                review_recommendation_page_num=st.number_input(f"페이지 넘버(1~{(len(review_recommendation)//10)+1})",min_value=1,
                                                                                max_value=(len(review_recommendation)//10)+1,value=1,step=1,
                                                                                key="review_recommendation_page_num")

                                
                                
                            if review_recommendation_page_num==(len(review_recommendation)//10)+1:
                                subset_review_recommendation=dict(list(review_recommendation.items())[10*(review_recommendation_page_num-1):])
                            else:
                                subset_review_recommendation=dict(list(review_recommendation.items())[10*(review_recommendation_page_num-1):10*(review_recommendation_page_num)])
 
                            recommendation_container_list1=[]
                            for i in range(len(subset_review_recommendation)):
                                recommendation_container_list1.append(st.container())
                                
                            for i, (key, value) in enumerate(subset_review_recommendation.items()):
                                question_id=int(key)
                                question_name=value[0]
                                level_name=value[1]
                                level_id=int(value[2])
                                recommend_type=value[3]
                                with recommendation_container_list1[i]:
                                    with st.expander(f"**:green[{recommend_type} # {str(question_id)}]**       **{question_name}**",expanded=True):
                                        ts=""
                                        if len(questions_tags_in_review[question_id])!=0:
                                            for i in range(len(questions_tags_in_review[question_id])):
                                                ts=ts+"#"+str(questions_tags_in_review[question_id][i])+"&nbsp;"
                                        tag = f'<p><span style="font-size: 13px; color: {tools.level_to_colorcode(level_id)}"><b>{level_name}&nbsp;</b></span><span style="font-size: 10px">{ts}</span></p>'
                                        st.markdown(tag, unsafe_allow_html=True)
                                        question_url = f"https://www.acmicpc.net/problem/{question_id}"
                                        st.markdown(f'''
                                                <a href={question_url}><button class="button button1">백준에서 보기</button></a>
                                                ''',
                                                unsafe_allow_html=True)
                            
                    # TODO 여기 살려야함
                        else:
                            selected_review_questions_ids=[]
                            for k,v in questions_tags_in_review.items():
                                if list(set(recommendation_multiselect1) & set(v)):
                                    selected_review_questions_ids.append(k)
                            selected_review_recommendation = {int(key): value for key, value in review_recommendation.items() if int(key) in selected_review_questions_ids}
                            ppcol1,ppcol2=st.columns([4,1])
                            with ppcol2:
                                selected_review_recommendation_page_num=st.number_input(f"페이지 넘버(1~{(len(selected_review_recommendation)//10)+1})",min_value=1,
                                                                                max_value=(len(selected_review_recommendation)//10)+1,value=1,step=1,
                                                                                key="selected_review_recommendation_page_num")

                                
                                
                            if selected_review_recommendation_page_num==(len(selected_review_recommendation)//10)+1:
                                subset_review_recommendation=dict(list(selected_review_recommendation.items())[10*(selected_review_recommendation_page_num-1):])
                            else:
                                subset_review_recommendation=dict(list(selected_review_recommendation.items())[10*(selected_review_recommendation_page_num-1):10*(selected_review_recommendation_page_num)])
 
                            recommendation_container_list1=[]
                            for i in range(len(subset_review_recommendation)):
                                recommendation_container_list1.append(st.container())
                                
                            for i, (key, value) in enumerate(subset_review_recommendation.items()):
                                question_id=int(key)
                                question_name=value[0]
                                level_name=value[1]
                                level_id=int(value[2])
                                recommend_type=value[3]
                                with recommendation_container_list1[i]:
                                    with st.expander(f"**:green[{recommend_type} # {str(question_id)}]**       **{question_name}**",expanded=True):
                                        ts=""
                                        if len(questions_tags_in_review[question_id])!=0:
                                            for i in range(len(questions_tags_in_review[question_id])):
                                                ts=ts+"#"+str(questions_tags_in_review[question_id][i])+"&nbsp;"
                                        tag = f'<p><span style="font-size: 13px; color: {tools.level_to_colorcode(level_id)}"><b>{level_name}&nbsp;</b></span><span style="font-size: 10px">{ts}</span></p>'
                                        st.markdown(tag, unsafe_allow_html=True)
                                        question_url = f"https://www.acmicpc.net/problem/{question_id}"
                                        st.markdown(f'''
                                                <a href={question_url}><button class="button button1">백준에서 보기</button></a>
                                                ''',
                                                unsafe_allow_html=True)
                                                                    
        with tab4:
            container5= st.container()
            with container5:
                preview_recommendation=recommendation["예습"]
                if len(preview_recommendation)!=0:
                    if "questions_tags_in_preview" not in st.session_state:
                        params_get_recommendation_tags={}
                        param_types_get_recommendation_tags={}
                        for i, (key, value) in enumerate(preview_recommendation.items()):
                            params_get_recommendation_tags[f"q{i}"]=key
                            param_types_get_recommendation_tags[f"q{i}"]= spanner.param_types.INT64

                        sql_get_recommendation_tags="SELECT question_id,ko_name tag_name FROM question_tag_relation A, tag B WHERE A.question_id in "
                        sql_get_recommendation_tags+='('+','.join([f"@q{i}" for i in range(len(preview_recommendation))])+') '
                        sql_get_recommendation_tags+="AND A.tag_id=B.id"
                        with database.snapshot() as snapshot:
                            result_get_recommendation_tags= snapshot.execute_sql(
                                sql_get_recommendation_tags,
                                params=params_get_recommendation_tags,
                                param_types=param_types_get_recommendation_tags
                            )
                        result_get_recommendation_tags=list(iter(result_get_recommendation_tags))
                        tsts=defaultdict(list)
                        for i in result_get_recommendation_tags:
                            tsts[i[0]].append(i[1])
                        st.session_state["questions_tags_in_preview"]=tsts
                        questions_tags_in_preview=st.session_state["questions_tags_in_preview"]
                    else:
                        questions_tags_in_preview=st.session_state["questions_tags_in_preview"]
                c51,c52= st.columns([3,9])
                with c51:
                    if "preview_recommendation_tags_name_list" not in st.session_state:
                        preview_recommendation_tags_name_list=list(set(itertools.chain.from_iterable(questions_tags_in_preview.values())))
                        st.session_state["preview_recommendation_tags_name_list"]=preview_recommendation_tags_name_list
                    else:
                        preview_recommendation_tags_name_list=st.session_state["preview_recommendation_tags_name_list"]
                    recommendation_multiselect2 = st.multiselect(
                        '큐레이션을 원하는 태그들을 선택해주세요 :)',
                        preview_recommendation_tags_name_list,[],max_selections=5,key="recommendation_multiselect2")
                    st.info("1개 이상 5개 이하의 태그를 선택해주세요.")
                with c52:
                    # TODO 만약 100개 들어온다면 페이지 기능 추가 / questions_tags_in_review 이거 하나씩 스패너에 요청하지 말고 한꺼번에 in 걸어서 받고 그 안에서 검색하는 식으로 하자 
                        if not recommendation_multiselect2:
                            pcol3,pcol4=st.columns([4,1])
                            with pcol4:
                                preview_recommendation_page_num=st.number_input(f"페이지 넘버(1~{(len(preview_recommendation)//10)+1})",min_value=1,
                                                                                max_value=(len(preview_recommendation)//10)+1,value=1,step=1,
                                                                                key="preview_recommendation_page_num")

                                
                                
                            if preview_recommendation_page_num==(len(preview_recommendation)//10)+1:
                                subset_preview_recommendation=dict(list(preview_recommendation.items())[10*(preview_recommendation_page_num-1):])
                            else:
                                subset_preview_recommendation=dict(list(preview_recommendation.items())[10*(preview_recommendation_page_num-1):10*(preview_recommendation_page_num)])
 
                            recommendation_container_list2=[]
                            for i in range(len(subset_preview_recommendation)):
                                recommendation_container_list2.append(st.container())
                                
                            for i, (key, value) in enumerate(subset_preview_recommendation.items()):
                                question_id=int(key)
                                question_name=value[0]
                                level_name=value[1]
                                level_id=int(value[2])
                                recommend_type=value[3]
                                with recommendation_container_list2[i]:
                                    with st.expander(f"**:green[{recommend_type} # {str(question_id)}]**       **{question_name}**",expanded=True):
                                        ts=""
                                        if len(questions_tags_in_preview[question_id])!=0:
                                            for i in range(len(questions_tags_in_preview[question_id])):
                                                ts=ts+"#"+str(questions_tags_in_preview[question_id][i])+"&nbsp;"
                                        tag = f'<p><span style="font-size: 13px; color: {tools.level_to_colorcode(level_id)}"><b>{level_name}&nbsp;</b></span><span style="font-size: 10px">{ts}</span></p>'
                                        st.markdown(tag, unsafe_allow_html=True)
                                        question_url = f"https://www.acmicpc.net/problem/{question_id}"
                                        st.markdown(f'''
                                                <a href={question_url}><button class="button button1">백준에서 보기</button></a>
                                                ''',
                                                unsafe_allow_html=True)
                            
                    # TODO 여기 살려야함
                        else:
                            selected_preview_questions_ids=[]
                            for k,v in questions_tags_in_preview.items():
                                if list(set(recommendation_multiselect2) & set(v)):
                                    selected_preview_questions_ids.append(k)
                            selected_preview_recommendation = {int(key): value for key, value in preview_recommendation.items() if int(key) in selected_preview_questions_ids}
                            ppcol3,ppcol4=st.columns([4,1])
                            with ppcol4:
                                selected_preview_recommendation_page_num=st.number_input(f"페이지 넘버(1~{(len(selected_preview_recommendation)//10)+1})",min_value=1,
                                                                                max_value=(len(selected_preview_recommendation)//10)+1,value=1,step=1,
                                                                                key="selected_preview_recommendation_page_num")

                                
                                
                            if selected_preview_recommendation_page_num==(len(selected_preview_recommendation)//10)+1:
                                subset_preview_recommendation=dict(list(selected_preview_recommendation.items())[10*(selected_preview_recommendation_page_num-1):])
                            else:
                                subset_preview_recommendation=dict(list(selected_preview_recommendation.items())[10*(selected_preview_recommendation_page_num-1):10*(selected_preview_recommendation_page_num)])
 
                            recommendation_container_list2=[]
                            for i in range(len(subset_preview_recommendation)):
                                recommendation_container_list2.append(st.container())
                                
                            for i, (key, value) in enumerate(subset_preview_recommendation.items()):
                                question_id=int(key)
                                question_name=value[0]
                                level_name=value[1]
                                level_id=int(value[2])
                                recommend_type=value[3]
                                with recommendation_container_list2[i]:
                                    with st.expander(f"**:green[{recommend_type} # {str(question_id)}]**       **{question_name}**",expanded=True):
                                        ts=""
                                        if len(questions_tags_in_preview[question_id])!=0:
                                            for i in range(len(questions_tags_in_preview[question_id])):
                                                ts=ts+"#"+str(questions_tags_in_preview[question_id][i])+"&nbsp;"
                                        tag = f'<p><span style="font-size: 13px; color: {tools.level_to_colorcode(level_id)}"><b>{level_name}&nbsp;</b></span><span style="font-size: 10px">{ts}</span></p>'
                                        st.markdown(tag, unsafe_allow_html=True)
                                        question_url = f"https://www.acmicpc.net/problem/{question_id}"
                                        st.markdown(f'''
                                                <a href={question_url}><button class="button button1">백준에서 보기</button></a>
                                                ''',
                                                unsafe_allow_html=True)
                            
