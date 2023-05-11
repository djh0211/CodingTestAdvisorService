import requests
import json
from user_agent import generate_user_agent, generate_navigator
import os
import sys
import pandas as pd
from tqdm import tqdm
import csv
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import streamlit as st
import itertools
import numpy as np



from google.cloud import spanner
from google.api_core import exceptions

def get_sample_q100():
    result=pd.read_csv("*****/q100.csv").values.tolist()
    result=list(itertools.chain.from_iterable(result))
    return result

def level_to_colorcode(level_id):
    if level_id==0:
        return "#000000"
    if level_id in list(range(1,6)):
        return "#a25b1f"
    if level_id in list(range(6,11)):
        return "#495e78"
    if level_id in list(range(11,16)):
        return "#e09e37"
    if level_id in list(range(16,21)):
        return "#6ddfa8"
    if level_id in list(range(21,26)):
        return "#50b1f6"
    if level_id in list(range(26,31)):
        return "#ea3364"
    if level_id == 31:
        return "#be8fe4"
    
def get_binary_result(x):
    if x[0]=="틀":
        x=0
    else:
        x=1
    return x
    
def return_week_list(start_date):
    import datetime
    
    end_date = datetime.date.today()

    date_list = []
    delta = datetime.timedelta(days=7)
    while start_date <= end_date:
        date_list.append(start_date.strftime('%Y/%m/%d'))
        start_date += delta
    b=pd.DataFrame()
    b["#week"]=date_list
    b['cnt']=[0]*len(date_list)
    
    return b

def return_month_list(start_date):
    import datetime
    end_date = datetime.date.today()
    
    
    t=[]
    start_year=start_date.year
    start_month=start_date.month
    end_year=end_date.year
    end_month=end_date.month
    
    for i in range(start_year,end_year+1):
        if i==start_year:
            for j in range(start_month,13):
                t.append(datetime.date(i,j,1).strftime('%Y/%m/%d'))
        elif i==end_year:
            for j in range(1,end_month+1):
                t.append(datetime.date(i,j,1).strftime('%Y/%m/%d'))
        else:
            for j in range(1,13):
                t.append(datetime.date(i,j,1).strftime('%Y/%m/%d'))
    
    b=pd.DataFrame()
    b["#month"]=t
    b['cnt']=[0]*len(t)       
        
    return b

def return_year_list(start_date):
    import datetime
    end_date = datetime.date.today()
    
    
    t=[]
    start_year=start_date.year
    end_year=end_date.year
    
    for i in range(start_year,end_year+1):
        t.append(datetime.date(i,1,1).strftime('%Y/%m/%d'))
    
    b=pd.DataFrame()
    b["#year"]=t
    b['cnt']=[0]*len(t)       
        
    return b
    
def level_id_to_level_name_from_spanner(database,level_id):
    with database.snapshot() as snapshot:
        result = snapshot.execute_sql(
            "SELECT name FROM level WHERE id=@name",
            params={"name":level_id},
            param_types={"name": spanner.param_types.INT64}
        )
    return next(iter(result))[0]

def get_piechart_colors():
    colors=["#9593b1"]
    colors.append("#231709")
    colors.append("#432616")
    colors.append("#65350f")
    colors.append("#80471c")
    colors.append("#795c34")
    
    colors.append("#5f6264")
    colors.append("#717577")
    colors.append("#84898b")
    colors.append("#979c9f")
    colors.append("#aab0b3")
    
    colors.append("#f9a603")
    colors.append("#ffd300")
    colors.append("#ffef00")
    colors.append("#eefc5e")
    colors.append("#fefbbd")
    
    colors.append("#2d7f48")
    colors.append("#3eb265")
    colors.append("#5aff91")
    colors.append("#9cffbd")
    colors.append("#bdffd3")
    
    colors.append("#1F4BE8")
    colors.append("#437FF9")
    colors.append("#4AA5F8")
    colors.append("#6DCEFC")
    colors.append("#A7F9F9")
    
    colors.append("#e0115f")
    colors.append("#e3296f")
    colors.append("#e9588f")
    colors.append("#ec709f")
    colors.append("#f3a0bf")
    
    return colors
    
def get_dic_level_name_to_level_id(database):
    with database.snapshot() as snapshot:
        result = snapshot.execute_sql(
            "SELECT * FROM level"
        )
    dic={}
    for i in list(iter(result))[1:-1]:
        dic[i[1]]=i[0]
        
    return dic
        

    
    
    

        

def df_to_list(dataframe:pd.DataFrame):
    """데이터프레임 -> [{},{},...]형태로"""
    return dataframe.to_dict('records')

def _get_timestamp(table):
    """시분초를 에폭 타임으로 변경해주는 func"""
    timestamp = []
    for data in table[0].find_all("a", class_="real-time-update"):
        timestamp.append(data.attrs['data-timestamp'])
    return timestamp

def id_check(user_id):
    p1= re.compile('[a-z0-9_]{3,20}')
    p2= re.compile('_{2,}')
    p3= re.compile('[a-z]{1,}')
    p_space= re.compile('\s')
    
    if p_space.findall(user_id):
        return -2 # 공백포함
    if p1.fullmatch(user_id):
        if user_id[0]!='_' and user_id[-1]!='_':
            if not p2.findall(user_id):
                if p3.findall(user_id):
                    if not user_id.isdigit():
                        return 1
            
                
    return -1
        


def is_user_in_baekjoon(user_id):
    """백준에 있는 유저인지 확인"""
    url = f"https://www.acmicpc.net/status?user_id={user_id}"
    ua = generate_user_agent(device_type='desktop')
    headers = {'User-Agent': ua}
    response= requests.get(url, headers=headers)
    req = response.text
    if response.status_code == requests.codes.ok:
        soup = BeautifulSoup(req, "html.parser")
        table = soup.select('table')
        df_table = pd.read_html(str(table))[0]
        if len(df_table)==0:
            return 0
        else:
            return 1
    else:
        return -1
    
    
# TODO: api call 개수 제한으로 서버리스로 구현해보면 어떨까?
def get_user_data_from_baekjoon(user_id):
    try:
        url = f"https://solved.ac/api/v3/user/show?handle={user_id}"
        headers = {"Content-Type": "application/json"}
        response = requests.get(url, headers=headers)
        return response.json()
        
    except:
        return -1
        


    
def get_full_correct_history_from_baekjoon(user_id):
    """백준에서 맞았습니다 학습기록만 수집"""
    url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=4"
    df_solved= pd.DataFrame()
    
    try:
        ua = generate_user_agent(device_type='desktop')
        headers = {'User-Agent': ua}
        response= requests.get(url, headers=headers)
        req = response.text
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(req, "html.parser")
            table = soup.select('table')
            timestamp = _get_timestamp(table)
            
            df_table = pd.read_html(str(table))[0]
            df_table['제출한 시간'] = timestamp
            df_table['아이디']=user_id
            
            solved_id= df_table.iloc[-1]["제출 번호"]
            df_solved= pd.concat([df_solved,df_table])
        while 1:
            url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=4&top={solved_id}"
            ua = generate_user_agent(device_type='desktop')
            headers = {'User-Agent': ua}
            response= requests.get(url, headers=headers)
            req = response.text
            if response.status_code == requests.codes.ok:
                soup = BeautifulSoup(req, "html.parser")
                table = soup.select('table')
                timestamp = _get_timestamp(table)
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id
                temp= df_table.iloc[-1]["제출 번호"]
                if solved_id==temp:
                    # print("기록수집끝")
                    # break
                    df_solved= df_solved.dropna()
                    return df_solved
                solved_id=temp
                df_solved= pd.concat([df_solved,df_table.iloc[1:]])
    except Exception:
        return pd.DataFrame()
        

def get_full_incorrect_history_from_baekjoon(user_id):
    """백준에서 틀렸습니다 학습기록만 수집"""
    url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=6"
    df_solved= pd.DataFrame()
    
    try:
        ua = generate_user_agent(device_type='desktop')
        headers = {'User-Agent': ua}
        response= requests.get(url, headers=headers)
        req = response.text
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(req, "html.parser")
            table = soup.select('table')
            timestamp = _get_timestamp(table)
            
            df_table = pd.read_html(str(table))[0]
            df_table['제출한 시간'] = timestamp
            df_table['아이디']=user_id
            
            solved_id= df_table.iloc[-1]["제출 번호"]
            df_solved= pd.concat([df_solved,df_table])
        while 1:
            url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=6&top={solved_id}"
            ua = generate_user_agent(device_type='desktop')
            headers = {'User-Agent': ua}
            response= requests.get(url, headers=headers)
            req = response.text
            if response.status_code == requests.codes.ok:
                soup = BeautifulSoup(req, "html.parser")
                table = soup.select('table')
                timestamp = _get_timestamp(table)
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id
                temp= df_table.iloc[-1]["제출 번호"]
                if solved_id==temp:
                    # print("기록수집끝")
                    # break
                    # TODO df_solved= df_solved.dropna()
                    return df_solved
                solved_id=temp
                df_solved= pd.concat([df_solved,df_table.iloc[1:]])
    except Exception:
        return pd.DataFrame()
    
    
def get_full_history_from_baekjoon(user_id):
    """백준에서 맞음,틀림 모든 학습기록 데이터프레임으로 받아온다

    Args:
        user_id (_type_): _description_

    Returns:
        full_df: pd.DataFrame
    """
    try:
        c_df=get_full_correct_history_from_baekjoon(user_id)
        ic_df=get_full_incorrect_history_from_baekjoon(user_id)
        if c_df.empty==True and ic_df.empty==True:
            raise
        full_df= pd.concat([c_df,ic_df])
        full_df= full_df.sort_values('제출한 시간',ascending=True)
        full_df= full_df.reset_index(drop=True)
        return full_df
    except Exception:
        return False
    
def get_additional_correct_history_from_baekjoon(user_id,database):
    """spanner에 없는 맞음 기록들만 백준에서 받아온다. 

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        _type_: _description_
    """
    url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=4"
    df_solved= pd.DataFrame()
    
    try:
        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                "SELECT submitted_epochtime FROM learning_history WHERE user_id = @name ORDER BY submitted_epochtime DESC LIMIT 1",
                params={"name": user_id},
                param_types={"name": spanner.param_types.STRING},
            )
        refreshed_epochtime= next(iter(results))[0]
        # print("refreshed_epochtime",refreshed_epochtime)        
        
        ua = generate_user_agent(device_type='desktop')
        headers = {'User-Agent': ua}
        response= requests.get(url, headers=headers)
        req = response.text
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(req, "html.parser")
            table = soup.select('table')
            timestamp = _get_timestamp(table)
            
            if str(refreshed_epochtime)>=max(timestamp):
                return pd.DataFrame()
            elif max(timestamp)>str(refreshed_epochtime) and str(refreshed_epochtime)>=min(timestamp):
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id
                df_table=df_table.loc[df_table["제출한 시간"] > str(refreshed_epochtime)]
                df_solved= pd.concat([df_solved,df_table])
                return df_solved
            else:
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id

                solved_id= df_table.iloc[-1]["제출 번호"]
                df_solved= pd.concat([df_solved,df_table])
        while 1:
            url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=4&top={solved_id}"
            ua = generate_user_agent(device_type='desktop')
            headers = {'User-Agent': ua}
            response= requests.get(url, headers=headers)
            req = response.text
            if response.status_code == requests.codes.ok:
                soup = BeautifulSoup(req, "html.parser")
                table = soup.select('table')
                timestamp = _get_timestamp(table)
                if str(refreshed_epochtime)>=max(timestamp):
                    return df_solved
                elif max(timestamp)>str(refreshed_epochtime) and str(refreshed_epochtime)>=min(timestamp):
                    df_table = pd.read_html(str(table))[0]
                    df_table['제출한 시간'] = timestamp
                    df_table['아이디']=user_id
                    df_table=df_table.loc[df_table["제출한 시간"] > str(refreshed_epochtime)]
                    df_solved= pd.concat([df_solved,df_table.iloc[1:]])

                    return df_solved
                else:
                    df_table = pd.read_html(str(table))[0]
                    df_table['제출한 시간'] = timestamp
                    df_table['아이디']=user_id

                    temp= df_table.iloc[-1]["제출 번호"]
                    if solved_id==temp:
                        return df_solved
                    df_solved= pd.concat([df_solved,df_table.iloc[1:]])
    except Exception:
        return pd.DataFrame()
        

def get_additional_incorrect_history_from_baekjoon(user_id,database):
    """spanner에 없는 틀림 기록들만 백준에서 받아온다. 

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        _type_: _description_
    """
    url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=6"
    df_solved= pd.DataFrame()
    
    try:
        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                "SELECT submitted_epochtime FROM learning_history WHERE user_id = @name ORDER BY submitted_epochtime DESC LIMIT 1",
                params={"name": user_id},
                param_types={"name": spanner.param_types.STRING},
            )
        refreshed_epochtime= next(iter(results))[0]
        # print("refreshed_epochtime",refreshed_epochtime)        
        
        ua = generate_user_agent(device_type='desktop')
        headers = {'User-Agent': ua}
        response= requests.get(url, headers=headers)
        req = response.text
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(req, "html.parser")
            table = soup.select('table')
            timestamp = _get_timestamp(table)
            
            if str(refreshed_epochtime)>=max(timestamp):
                return pd.DataFrame()
            elif max(timestamp)>str(refreshed_epochtime) and str(refreshed_epochtime)>=min(timestamp):
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id
                df_table=df_table.loc[df_table["제출한 시간"] > str(refreshed_epochtime)]
                df_solved= pd.concat([df_solved,df_table])
                return df_solved
            else:
                df_table = pd.read_html(str(table))[0]
                df_table['제출한 시간'] = timestamp
                df_table['아이디']=user_id

                solved_id= df_table.iloc[-1]["제출 번호"]
                df_solved= pd.concat([df_solved,df_table])
        while 1:
            url = f"https://www.acmicpc.net/status?user_id={user_id}&result_id=6&top={solved_id}"
            ua = generate_user_agent(device_type='desktop')
            headers = {'User-Agent': ua}
            response= requests.get(url, headers=headers)
            req = response.text
            if response.status_code == requests.codes.ok:
                soup = BeautifulSoup(req, "html.parser")
                table = soup.select('table')
                timestamp = _get_timestamp(table)
                if str(refreshed_epochtime)>=max(timestamp):
                    return df_solved
                elif max(timestamp)>str(refreshed_epochtime) and str(refreshed_epochtime)>=min(timestamp):
                    df_table = pd.read_html(str(table))[0]
                    df_table['제출한 시간'] = timestamp
                    df_table['아이디']=user_id
                    df_table=df_table.loc[df_table["제출한 시간"] > str(refreshed_epochtime)]
                    df_solved= pd.concat([df_solved,df_table.iloc[1:]])

                    return df_solved
                else:
                    df_table = pd.read_html(str(table))[0]
                    df_table['제출한 시간'] = timestamp
                    df_table['아이디']=user_id

                    temp= df_table.iloc[-1]["제출 번호"]
                    if solved_id==temp:
                        return df_solved
                    df_solved= pd.concat([df_solved,df_table.iloc[1:]])
    except Exception:
        return pd.DataFrame()

def get_additional_history_from_baekjoon(user_id, database):
    """spanner에 없는 학습 기록들을 백준에서 가져온다.

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        _type_: _description_
    """
    c_df=get_additional_correct_history_from_baekjoon(user_id,database)
    ic_df=get_additional_incorrect_history_from_baekjoon(user_id,database)
    
    full_df= pd.concat([c_df,ic_df])
    if full_df.empty==False:
        full_df=full_df.dropna(subset=["제출 번호","아이디","문제","결과","제출한 시간"])

        full_df= full_df.sort_values('제출한 시간',ascending=True)
        full_df= full_df.reset_index(drop=True)
    
    return full_df


    
        

# TODO 추천 문제 제공 모델 input에 사용할 수 있게 가공
def preprocess_recs():
    """TODO 추천 문제 제공 모델 input에 사용할 수 있게 가공"""
    pass
    
# TODO 통계 제공 모델 input에 사용할 수 있게 가공
def preprocess_stats():
    """TODO 통계 제공 모델 input에 사용할 수 있게 가공"""
    pass

# TODO 엔드포인트에 인풋을 제공하는 함수
def give_input_to_endpoint():
    """TODO 엔드포인트에 인풋을 제공하는 함수"""
    pass

'''여기서부터 spanner 사용'''

def is_user_in_spanner(user_id, database):
    """우리 DB에 있는 유저인지

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        BOOL: 있으면 True 리턴, 없으면 False 리턴
    """
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT COUNT(*) FROM user "
            "WHERE id = @name",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
    for i in results:
        if i[0]==0:
            return False
        else:
            return True
        
def is_user_registered(user_id, database):
    """user-registered 값을 return

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        _type_: _description_
    """
    
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT registered FROM user "
            "WHERE id = @name",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
        for i in results:
            temp=i
        results=temp
    if results[0]==True:
        return True
    else:
        return False

# TODO user 테이블로 변경 필요
def get_user_data_from_spanner(user_id,database):
    """Spanner에 저장되어있는 유저데이터를 가져옴

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        _type_: _description_
    """
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT * FROM user "
            "WHERE id = @name",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
    results= next(iter(results))
    if results==[]:
        return False
    else:
        temp={}
        temp["id"]=results[0]
        temp["registered"]=results[1]
        temp["level_id"]=results[2]
        temp["refreshed_epochtime"]=results[3]
        temp["solvedac_rank"]=results[4]
        temp["solvedCount"]=results[5]
        temp["user_class"]=results[6]
        temp["rating"]=results[7]
        temp["ratingByProblemsSum"]=results[8]
        temp["ratingByClass"]=results[9]
        temp["ratingBySolvedCount"]=results[10]
        temp["exp_point"]=results[11]
        temp["maxStreak"]=results[12]
        return temp
    

def history_list_to_df(arr):
    col=["id", "user_id", "question_id","result",
                        "consumed_memory","consumed_time","code_length",
                        "submitted_epochtime"]
    df=pd.DataFrame(data=arr,index=range(len(arr)),columns=col)
    df=df.sort_values("submitted_epochtime")
    df=df.reset_index(drop=True)
    return df

# TODO learning_history로 변경 필요!!!
def get_history_from_spanner(user_id,database):
    """Spanner에 저장되어있는 학습기록을 가져옴

    Args:
        user_id (_type_): _description_
        database (_type_): _description_

    Returns:
        있으면 list 없으면 False
    """
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT * FROM learning_history "
            "WHERE user_id = @name",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
    results= list(iter(results))
    if results==[]:
        return False
    else:
        return results

def preprocess_history_data_to_insert_spanner(user_history_df):
    """백준에서 기록 수집해서 스패너에 넣기 전 리스트화

    Args:
        user_history_df (pd.DataFrame): _description_

    Returns:
        user_history: list
    """
    user_history_df=user_history_df.drop(columns=["언어"])
    user_history_df = user_history_df.astype({"제출 번호":'int64'})
    user_history_df = user_history_df.astype({"아이디":'string'})
    user_history_df = user_history_df.astype({"결과":'string'})
    user_history_df = user_history_df.astype({"코드 길이":'float64'})
    user_history_df = user_history_df.astype({"제출한 시간":'int64'})
    user_history= user_history_df.values.tolist()
    def fun1(x):
        x[4]=float(x[4])
        x[5]=float(x[5])
        x[6]=float(x[6])
        return x
    user_history=list(map(fun1,user_history))
    
    
    return user_history


# TODO learning_history 테이블로 변경 필요!!
def insert_history_data_to_spanner(database,data):
    """Inserts sample data into the given database.

    The database and table must already exist and can be created using
    `create_database`.
    """
    try:
        with database.batch() as batch:
            batch.insert(
                table="learning_history",
                columns=("id", "user_id", "question_id","result",
                        "consumed_memory","consumed_time","code_length",
                        "submitted_epochtime"),
                values=data,
            )
    except exceptions.AlreadyExists as e:
        # try to pass duplicate record
        pass
    # except exceptions.
    
    #     raise
    #     return -1

# TODO learning_history로 바꿔야함!!! 
def preprocess_new_user_data_to_insert_spanner(database,user_id):
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT submitted_epochtime FROM learning_history WHERE user_id = @name ORDER BY submitted_epochtime DESC LIMIT 1",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
    timestamp= next(iter(results))[0] #int
    user_json= get_user_data_from_baekjoon(user_id)
    if user_json==-1:
        return -1
    
    temp={}
    temp["id"]=user_json["handle"]
    temp["registered"]=True
    temp["level_id"]=user_json["tier"]
    temp["refreshed_epochtime"]=timestamp
    temp["solvedac_rank"]=user_json["rank"]
    temp["solvedCount"]=user_json["solvedCount"]
    temp["user_class"]=user_json["class"]
    temp["rating"]=user_json["rating"]
    temp["ratingByProblemsSum"]=user_json["ratingByProblemsSum"]
    temp["ratingByClass"]=user_json["ratingByClass"]
    temp["ratingBySolvedCount"]=user_json["ratingBySolvedCount"]
    temp["exp_point"]=user_json["ratingBySolvedCount"]
    temp["maxStreak"]=user_json["maxStreak"]
    temp=pd.DataFrame(temp,index=[0])
    user_data=temp.values.tolist()
    
    return user_data

# TODO: user 테이블로 변경 필요!!!!
def insert_user_data_to_spanner(database,user_id):
    user_data= preprocess_new_user_data_to_insert_spanner(database,user_id)
    if user_data==-1:
        return -2 # solved ac 미등록 유저
    try:
        with database.batch() as batch:
            batch.insert(
                table="user",
                columns=("id", "registered", "level_id","refreshed_epochtime",
                            "solvedac_rank","solvedCount","user_class",
                            "rating","ratingByProblemsSum", "ratingByClass", "ratingBySolvedCount",
                            "exp_point", "maxStreak"),
                values=user_data,
            )
    except Exception:
        return -1
def update_user_data_all(transaction,data):
                        transaction.update(
                            table="user",
                            columns=("id", "registered", "level_id","refreshed_epochtime",
                                    "solvedac_rank","solvedCount","user_class",
                                    "rating","ratingByProblemsSum", "ratingByClass", "ratingBySolvedCount",
                                    "exp_point", "maxStreak"),
                            values=data,
                        )
def control_update_user_data_all(database,user_id):
    user_data= preprocess_new_user_data_to_insert_spanner(database,user_id)
    database.run_in_transaction(update_user_data_all,data=user_data)


# TODO 작동오류,,,,
def update_registered_value(transaction,user_id,registered_value:bool):
    try:
        transaction.execute_update(
        "UPDATE user SET registered = @RegisteredValue WHERE id = @name",
        params={"RegisteredValue":registered_value,
                "name": user_id},
        param_types={"RegisteredValue":spanner.param_types.BOOL,
                     "name": spanner.param_types.STRING},
        )
        return 1
    except Exception:
        return -1



    
def update_refreshed_epochtime(transaction,user_id,epochtime):
    try:
        transaction.execute_update(
        "UPDATE user SET refreshed_epochtime = @epochtime WHERE id = @name",
        params={"epochtime":epochtime,
                "name": user_id},
        param_types={"epochtime":spanner.param_types.INT64,
                     "name": spanner.param_types.STRING},
        )
        return 1
    except Exception:
        return -1

def update_user_data_to_spanner(format:str,database,
                                user_id:str,registered_value:bool=True,
                                epochtime=0):
    """스패너의 유저 정보를 수정한다.

    Args:
        format (str): _description_
        database (_type_): _description_
        user_id (_type_): _description_
        registered_value (_type_): _description_
    """
    
    # if format not in ["registered","refreshed_epochtime"]:
    if format not in ["refreshed_epochtime"]:
        return -2
    
    # if format=="regisitered":
    #     res=database.run_in_transaction(update_registered_value,
    #                                 user_id=user_id,
    #                                 registered_value=registered_value)
    #     if res==-1:
    #         return -1
    if format== "refreshed_epochtime":
        res=database.run_in_transaction(update_refreshed_epochtime,
                                    user_id=user_id,
                                    epochtime=epochtime)
        if res==-1:
            return -1
        
def get_refreshed_epochtime_from_spanner(database,user_id):
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "SELECT submitted_epochtime FROM learning_history WHERE user_id = @name ORDER BY submitted_epochtime DESC LIMIT 1",
            params={"name": user_id},
            param_types={"name": spanner.param_types.STRING},
        )
    timestamp= next(iter(results))[0]
    return timestamp

# WHERE user_id="djh0211" AND DATE(TIMESTAMP_SECONDS(submitted_epochtime)) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)

def get_my_level_distribution_stats_per_period(database,user_id,num_period):
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "WITH my_history AS (SELECT * FROM learning_history WHERE user_id = @name AND DATE(TIMESTAMP_SECONDS(submitted_epochtime)) >= DATE_SUB(CURRENT_DATE(), INTERVAL @num1 DAY)),"
            "unique_question AS (SELECT DISTINCT(question_id) FROM my_history WHERE result LIKE @p1 OR result LIKE @p2),"
            "tmp AS (SELECT level_id,COUNT(level_id) cnt FROM unique_question A LEFT JOIN question B ON A.question_id=B.id GROUP BY 1 ORDER BY 1)"
            "SELECT A.name,CASE WHEN cnt IS NULL THEN 0 ELSE cnt END cnt FROM level A LEFT JOIN tmp B ON A.id=B.level_id ORDER BY id",
            params={"name": user_id,"num1":num_period ,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                            "num1": spanner.param_types.INT64,
                            "p1": spanner.param_types.STRING,
                            "p2": spanner.param_types.STRING}
        )
    results= list(iter(results))[1:-1]
    level_name_ll = list(map(lambda x:x[0],results))
    level_cnt_ll = list(map(lambda x:x[1],results))
    level_distribution = dict(zip(level_name_ll, level_cnt_ll))
    
    return level_distribution,level_name_ll,level_cnt_ll

def get_my_level_distribution_stats(database,user_id):
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            "WITH my_history AS (SELECT * FROM learning_history WHERE user_id = @name),"
            "unique_question AS (SELECT DISTINCT(question_id) FROM my_history WHERE result LIKE @p1 OR result LIKE @p2),"
            "tmp AS (SELECT level_id,COUNT(level_id) cnt FROM unique_question A LEFT JOIN question B ON A.question_id=B.id GROUP BY 1 ORDER BY 1)"
            "SELECT A.name,CASE WHEN cnt IS NULL THEN 0 ELSE cnt END cnt FROM level A LEFT JOIN tmp B ON A.id=B.level_id ORDER BY id",
            params={"name": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                            "p1": spanner.param_types.STRING,
                            "p2": spanner.param_types.STRING}
        )
    results= list(iter(results))[1:-1]
    level_name_ll = list(map(lambda x:x[0],results))
    level_cnt_ll = list(map(lambda x:x[1],results))
    level_distribution = dict(zip(level_name_ll, level_cnt_ll))
    
    return level_distribution,level_name_ll,level_cnt_ll

  # TODO 리스트로 간단히 정리해서 넣자 sql 및 params
def get_my_tag_distribution_stats_per_period(database,user_id,num_period):
    with database.snapshot() as snapshot:
        results2 = snapshot.execute_sql(
            "WITH my_history AS (SELECT * FROM learning_history WHERE user_id = @name AND DATE(TIMESTAMP_SECONDS(submitted_epochtime)) >= DATE_SUB(CURRENT_DATE(), INTERVAL @num1 DAY)),"
            "unique_question AS (SELECT DISTINCT(question_id) FROM my_history WHERE result LIKE @p1 OR result LIKE @p2),"
            "tmp AS (SELECT A.* FROM question_tag_relation A INNER JOIN unique_question B ON A.question_id=B.question_id),"
            "tmp2 AS (SELECT A.*,B.ko_name FROM tmp A INNER JOIN tag B ON A.tag_id=B.id)"
            "SELECT tag_id,ko_name, COUNT(tag_id) cnt FROM tmp2 GROUP BY 1,2 ORDER BY 3 DESC",
            params={"name": user_id,"num1":num_period ,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                            "num1": spanner.param_types.INT64,
                            "p1": spanner.param_types.STRING,
                            "p2": spanner.param_types.STRING}
        )
    return list(iter(results2))

def get_my_tag_distribution_stats(database,user_id):
    with database.snapshot() as snapshot:
        results2 = snapshot.execute_sql(
            "WITH my_history AS (SELECT * FROM learning_history WHERE user_id = @name),"
            "unique_question AS (SELECT DISTINCT(question_id) FROM my_history WHERE result LIKE @p1 OR result LIKE @p2),"
            "tmp AS (SELECT A.* FROM question_tag_relation A INNER JOIN unique_question B ON A.question_id=B.question_id),"
            "tmp2 AS (SELECT A.*,B.ko_name FROM tmp A INNER JOIN tag B ON A.tag_id=B.id)"
            "SELECT tag_id,ko_name, COUNT(tag_id) cnt FROM tmp2 GROUP BY 1,2 ORDER BY 3 DESC",
            params={"name": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                            "p1": spanner.param_types.STRING,
                            "p2": spanner.param_types.STRING}
        )
    return list(iter(results2))


def get_recommendation(database,user_id,options):
    """추천문제를 받아오는 메서드, 현재는 spanner에서 해당 태그의 문제를 랜덤 10개 가져옴

    Args:
        database (_type_): _description_
        user_id (_type_): _description_
        options (_type_): _description_

    Returns:
        _type_: _description_
    """
    if len(options)==1:
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                "WITH selected_options AS (SELECT id,ko_name FROM tag WHERE ko_name=@option1),"
                "tmp1 AS (SELECT A.* FROM question_tag_relation A,selected_options B WHERE A.tag_id=B.id),"
                "level AS (SELECT name level_name, id level_id FROM level),"
                "tmp2 AS (SELECT A.*,title, level_id FROM tmp1 A,question B WHERE A.question_id=B.id),"
                "tmp3 AS (SELECT question_id,title,level_name,A.level_id FROM tmp2 A,level B WHERE A.level_id=B.level_id)"
                "SELECT * FROM tmp3 TABLESAMPLE RESERVOIR (10 ROWS)",
                params={"option1":options[0]},
                param_types={"option1": spanner.param_types.STRING}
            )
    if len(options)==2:
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                "WITH selected_options AS (SELECT id,ko_name FROM tag WHERE ko_name=@option1 OR ko_name=@option2),"
                "tmp1 AS (SELECT A.* FROM question_tag_relation A,selected_options B WHERE A.tag_id=B.id),"
                "level AS (SELECT name level_name, id level_id FROM level),"
                "tmp2 AS (SELECT A.*,title, level_id FROM tmp1 A,question B WHERE A.question_id=B.id),"
                "tmp3 AS (SELECT question_id,title,level_name,A.level_id FROM tmp2 A,level B WHERE A.level_id=B.level_id)"
                "SELECT * FROM tmp3 TABLESAMPLE RESERVOIR (10 ROWS)",
                params={"option1":options[0],"option2":options[1]},
                param_types={"option1": spanner.param_types.STRING,
                             "option2": spanner.param_types.STRING}
            )
    if len(options)==3:
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                "WITH selected_options AS (SELECT id,ko_name FROM tag WHERE ko_name=@option1 OR ko_name=@option2 OR ko_name=@option3),"
                "tmp1 AS (SELECT A.* FROM question_tag_relation A,selected_options B WHERE A.tag_id=B.id),"
                "level AS (SELECT name level_name, id level_id FROM level),"
                "tmp2 AS (SELECT A.*,title, level_id FROM tmp1 A,question B WHERE A.question_id=B.id),"
                "tmp3 AS (SELECT question_id,title,level_name,A.level_id FROM tmp2 A,level B WHERE A.level_id=B.level_id)"
                "SELECT * FROM tmp3 TABLESAMPLE RESERVOIR (10 ROWS)",
                params={"option1":options[0],"option2":options[1],"option3":options[2]},
                param_types={"option1": spanner.param_types.STRING,
                             "option2": spanner.param_types.STRING,
                             "option3": spanner.param_types.STRING}
            )
    if len(options)==4:
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                "WITH selected_options AS (SELECT id,ko_name FROM tag WHERE ko_name=@option1 OR ko_name=@option2 OR ko_name=@option3 OR ko_name=@option4),"
                "tmp1 AS (SELECT A.* FROM question_tag_relation A,selected_options B WHERE A.tag_id=B.id),"
                "level AS (SELECT name level_name, id level_id FROM level),"
                "tmp2 AS (SELECT A.*,title, level_id FROM tmp1 A,question B WHERE A.question_id=B.id),"
                "tmp3 AS (SELECT question_id,title,level_name,A.level_id FROM tmp2 A,level B WHERE A.level_id=B.level_id)"
                "SELECT * FROM tmp3 TABLESAMPLE RESERVOIR (10 ROWS)",
                params={"option1":options[0],"option2":options[1],"option3":options[2],"option4":options[3]},
                param_types={"option1": spanner.param_types.STRING,
                             "option2": spanner.param_types.STRING,
                             "option3": spanner.param_types.STRING,
                             "option4": spanner.param_types.STRING}
            )
    if len(options)==5:
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                "WITH selected_options AS (SELECT id,ko_name FROM tag WHERE ko_name=@option1 OR ko_name=@option2 OR ko_name=@option3 OR ko_name=@option4 OR ko_name=@option5),"
                "tmp1 AS (SELECT A.* FROM question_tag_relation A,selected_options B WHERE A.tag_id=B.id),"
                "level AS (SELECT name level_name, id level_id FROM level),"
                "tmp2 AS (SELECT A.*,title, level_id FROM tmp1 A,question B WHERE A.question_id=B.id),"
                "tmp3 AS (SELECT question_id,title,level_name,A.level_id FROM tmp2 A,level B WHERE A.level_id=B.level_id)"
                "SELECT * FROM tmp3 TABLESAMPLE RESERVOIR (10 ROWS)",
                params={"option1":options[0],"option2":options[1],"option3":options[2],"option4":options[3],"option5":options[4]},
                param_types={"option1": spanner.param_types.STRING,
                             "option2": spanner.param_types.STRING,
                             "option3": spanner.param_types.STRING,
                             "option4": spanner.param_types.STRING,
                             "option5": spanner.param_types.STRING}
            )        
    
    return result


    
def get_question_tags_from_spanner(database,question_id):
    with database.snapshot() as snapshot:
        results4 = snapshot.execute_sql(
            "SELECT ko_name tag_name FROM question_tag_relation A, tag B WHERE A.tag_id=B.id AND A.question_id=@name",
            params={"name": int(question_id)},
            param_types={"name": spanner.param_types.INT64},
        )
    results4= list(iter(results4))
    # tag_id_ll=list(map(lambda x:x[0],results4))
    # tag_name_ll=list(map(lambda x:x[1],results4))
    
    results4=list(itertools.chain.from_iterable(results4))
    
    return results4

def get_statistics_graph_per_week(database,user_id):
    with database.snapshot() as snapshot:
        result4 = snapshot.execute_sql(
            "WITH A AS (SELECT * FROM learning_history WHERE result LIKE @p1 OR result LIKE @p2)"
            "SELECT DATE_TRUNC(DATE(TIMESTAMP_SECONDS(submitted_epochtime)), WEEK) AS week_start, COUNT(*) AS count FROM A WHERE user_id=@name GROUP BY week_start ORDER BY week_start",
            params={"name": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                        "p1": spanner.param_types.STRING,
                        "p2": spanner.param_types.STRING}
        )
    result4=list(iter(result4))
    number_of_week=list(map(lambda x:x[0].strftime("%Y/%m/%d"),result4))
    counts_per_week=list(map(lambda x:x[1],result4))
    
    chart_data=pd.DataFrame({
        '#week':number_of_week,
        'counts_per_week':counts_per_week
    })
    # week_on_week= chart_data.counts_per_week.diff()
    # chart_data['week_on_week']=np.where(week_on_week.isna(),0,week_on_week).astype('int')
    
    date_list_df=return_week_list(result4[0][0])
    
    chart_data= pd.merge(date_list_df,chart_data,on="#week",how="outer")
    chart_data= chart_data.replace(np.NaN,0)
    chart_data= chart_data.drop(columns=["cnt"])
    week_on_week= chart_data.counts_per_week.diff()
    chart_data['week_on_week']=np.where(week_on_week.isna(),0,week_on_week).astype('int')
    chart_data=chart_data.rename(columns={'#week':'index'}).set_index('index')
    chart_data["cumulative"]=chart_data["counts_per_week"]
    chart_data["cumulative"]=chart_data["cumulative"].cumsum()
    chart_data.columns = ["주차 별 풀이 문제 수", "전주 대비 풀이 문제 수 등락","누적 풀이 문제 수"]
    return chart_data





def get_statistics_graph_per_month(database,user_id):
    with database.snapshot() as snapshot:
        result4 = snapshot.execute_sql(
            "WITH A AS (SELECT * FROM learning_history WHERE result LIKE @p1 OR result LIKE @p2)"
            "SELECT DATE_TRUNC(DATE(TIMESTAMP_SECONDS(submitted_epochtime)), MONTH) AS month, COUNT(*) AS count FROM A WHERE user_id=@name GROUP BY month ORDER BY month",
            params={"name": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                        "p1": spanner.param_types.STRING,
                        "p2": spanner.param_types.STRING}
        )
    result4=list(iter(result4))
    number_of_month=list(map(lambda x:x[0].strftime("%Y/%m/%d"),result4))
    counts_per_month=list(map(lambda x:x[1],result4))

    chart_data=pd.DataFrame({
        '#month':number_of_month,
        'counts_per_month':counts_per_month
        })
    
    date_list_df=return_month_list(result4[0][0])

    chart_data= pd.merge(date_list_df,chart_data,on="#month",how="outer")
    chart_data= chart_data.replace(np.NaN,0)
    chart_data= chart_data.drop(columns=["cnt"])
    month_on_month= chart_data.counts_per_month.diff()
    chart_data['month_on_month']=np.where(month_on_month.isna(),0,month_on_month).astype('int')
    chart_data=chart_data.rename(columns={'#month':'index'}).set_index('index')
    chart_data["cumulative"]=chart_data["counts_per_month"]
    chart_data["cumulative"]=chart_data["cumulative"].cumsum()
    chart_data.columns = ["월간 풀이 문제 수", "전월 대비 풀이 문제 수 등락","누적 풀이 문제 수"]
    
    
    return chart_data


def get_statistics_graph_per_year(database,user_id):
    with database.snapshot() as snapshot:
        result4 = snapshot.execute_sql(
            "WITH A AS (SELECT * FROM learning_history WHERE result LIKE @p1 OR result LIKE @p2)"
            "SELECT DATE_TRUNC(DATE(TIMESTAMP_SECONDS(submitted_epochtime)), YEAR) AS year, COUNT(*) AS count FROM A WHERE user_id=@name GROUP BY year ORDER BY year",
            params={"name": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"name": spanner.param_types.STRING,
                        "p1": spanner.param_types.STRING,
                        "p2": spanner.param_types.STRING}
        )
    result4=list(iter(result4))
    number_of_year=list(map(lambda x:x[0].strftime("%Y/%m/%d"),result4))
    counts_per_year=list(map(lambda x:x[1],result4))

    chart_data=pd.DataFrame({
        '#year':number_of_year,
        'counts_per_year':counts_per_year
        })
    
    date_list_df=return_year_list(result4[0][0])

    chart_data= pd.merge(date_list_df,chart_data,on="#year",how="outer")
    chart_data= chart_data.replace(np.NaN,0)
    chart_data= chart_data.drop(columns=["cnt"])
    year_on_year= chart_data.counts_per_year.diff()
    chart_data['year_on_year']=np.where(year_on_year.isna(),0,year_on_year).astype('int')
    chart_data=chart_data.rename(columns={'#year':'index'}).set_index('index')
    chart_data["cumulative"]=chart_data["counts_per_year"]
    chart_data["cumulative"]=chart_data["cumulative"].cumsum()
    chart_data.columns = ["년별 풀이 문제 수", "전년 대비 풀이 문제 수 등락","누적 풀이 문제 수"]
    
    
    return chart_data


