import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

import os
import random
import numpy as np
import pandas as pd
import time

import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
import numpy as np
from collections import defaultdict
import pickle
import json
import itertools

import glob
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import spanner


app=FastAPI()
# 서비스 계정 키 JSON 파일 경로
key_path = glob.glob("***.json")[0]

# Credentials 객체 생성
credentials = service_account.Credentials.from_service_account_file(key_path)

client = bigquery.Client(credentials = credentials, 
                         project = credentials.project_id)


    
with open('/home/gcpwoong/backend/demo_v1/question_level_dic.json', 'r') as f:
    question_level_dic = json.load(f)
    
with open('/home/gcpwoong/backend/demo_v1/accuracy_per_question.json', 'r') as f:
    accuracy_per_question = json.load(f)
    
with open('/home/gcpwoong/backend/demo_v1/question_averagetry_dic.json', 'r') as f:
    question_averagetry_dic = json.load(f)
    
with open('/home/gcpwoong/backend/demo_v1/accuracy_per_tag_dic.json', 'r') as f:
    accuracy_per_tag_dic = json.load(f)
    
with open('/home/gcpwoong/backend/demo_v1/question_acc_dic.json', 'r') as f:
    question_acc_dic = json.load(f)
    
with open('/home/gcpwoong/backend/demo_v1/tag_dic.json', 'r') as f:
    tag_dic = json.load(f)
    
model_fname_ = "/home/gcpwoong/backend/demo_v1/new_trained_model1.pkl"
with open(model_fname_, 'rb') as f: 
    model= pickle.load(f)
    
spanner_client = spanner.Client()
instance = spanner_client.instance("instance******")
database = instance.database("db*******")
    
def get_my_history_df(user_id):
    sql=""
    sql+="WITH tmp AS (SELECT * FROM learning_history WHERE user_id=@id) "
    sql+="SELECT user_id,question_id, CASE WHEN result LIKE @p1 OR result LIKE @p2 THEN 1 ELSE 0 END new_result,submitted_epochtime "
    sql+="FROM tmp ORDER BY submitted_epochtime"
    with database.snapshot() as snapshot:
        results = snapshot.execute_sql(
            sql,
            params={"id": user_id,"p1":"맞았%","p2":"100점%"},
            param_types={"id": spanner.param_types.STRING},
        )
    results=list(iter(results))
    my_history_df=pd.DataFrame(results,columns=["user_id","question_id","result","submitted_epochtime"])
    
    my_history_df["averageTries"]=my_history_df["question_id"].astype(str).map(question_averagetry_dic)
    my_history_df["accuracy_per_question"]=my_history_df["question_id"].astype(str).map(accuracy_per_question)
    my_history_df["tag"]=my_history_df["question_id"].astype(str).map(tag_dic)
    my_history_df["accuracy_per_tag"]=my_history_df["tag"].astype(str).map(accuracy_per_tag_dic)
    my_history_df["level_id"]=my_history_df["question_id"].astype(str).map(question_level_dic)
    
    my_history_df["temp_for_relative"]=(100*my_history_df["result"]-my_history_df["accuracy_per_question"])
    my_history_df["cumulated_points"]=my_history_df.groupby(["user_id"])["temp_for_relative"].cumsum().shift(fill_value=0)
    my_history_df.drop(columns="temp_for_relative")
    # 이전 문제 정답 횟수
    my_history_df['prior_correct_count'] = my_history_df.groupby('user_id')['result'].cumsum().shift(fill_value=0)
    my_history_df['prior_count'] = my_history_df.groupby('user_id')['result'].cumcount().fillna(0)
    idxs=my_history_df.loc[my_history_df["prior_count"]<my_history_df["prior_correct_count"]].index
    my_history_df.loc[idxs, ['prior_correct_count', 'prior_accuracy']] = 0

    my_history_df['prior_accuracy'] = round(100*(my_history_df['prior_correct_count'] / my_history_df['prior_count'])).fillna(0)
    my_history_df['prior_accuracy']=my_history_df['prior_accuracy'].astype(int)

    my_history_df["prior_tag_correct_count"]=my_history_df.groupby(['user_id',"tag"])['result'].cumsum().shift(fill_value=0)
    my_history_df["prior_tag_count"]=my_history_df.groupby(['user_id',"tag"])['result'].cumcount().fillna(0)
    idxs=my_history_df.loc[my_history_df["prior_tag_count"]<my_history_df["prior_tag_correct_count"]].index
    my_history_df.loc[idxs, ['prior_tag_correct_count', 'prior_tag_accuracy']] = 0
    my_history_df['prior_tag_accuracy'] = round(100*(my_history_df['prior_tag_correct_count'] / my_history_df['prior_tag_count']).fillna(0)).astype(int)
    
    return my_history_df  

def get_target_review_questions(user_id):
    sql=""
    sql+="SELECT DISTINCT(question_id) FROM learning_history WHERE user_id=@id GROUP BY question_id"
    with database.snapshot() as snapshot:
        A = snapshot.execute_sql(
            sql,
            params={"id": user_id},
            param_types={"id": spanner.param_types.STRING},
        )
    A = list(iter(A))
    A = list(itertools.chain(*list((A))))
    return A

class review_recommendation_input(BaseModel):
    user_id: str
class preview_recommendation_input(BaseModel):
    user_id: str
    level_id: int
class prediction_input(BaseModel):
    user_id: str
    codingtest_question_list: list
    
@app.post('/review_recommendation/')
async def get_review_recommendation(item:review_recommendation_input):
    user_id=item.user_id
    my_history_df=get_my_history_df(user_id)
    df_mylastrow=my_history_df.iloc[-1]
    questions=get_target_review_questions(user_id)
    inference_df=pd.DataFrame()
    FEATS = ["question_id","level_id",
            "averageTries","lag_time","accuracy_per_question","tag","accuracy_per_tag",
            "cumulated_points","prior_correct_count","prior_count","prior_accuracy","prior_tag_correct_count",
            "prior_tag_count","prior_tag_accuracy"]
    for question_id in questions:
        df_question_mylastrow=my_history_df.loc[(my_history_df["question_id"]==question_id)].iloc[-1]
        lag_time=int(time.time())-df_mylastrow.submitted_epochtime
        test_row=[df_question_mylastrow.question_id,df_question_mylastrow.level_id,df_question_mylastrow.averageTries,
                lag_time,df_question_mylastrow.accuracy_per_question,df_question_mylastrow.tag,
                df_question_mylastrow.accuracy_per_tag,df_mylastrow.cumulated_points,
                df_mylastrow.prior_correct_count,df_mylastrow.prior_count,df_mylastrow.prior_accuracy,
                df_question_mylastrow.prior_tag_correct_count,df_question_mylastrow.prior_tag_count,df_question_mylastrow.prior_tag_accuracy]
        one_row=pd.DataFrame([test_row],columns=FEATS)
        inference_df=pd.concat([inference_df,one_row])
    total_preds = model.predict(inference_df[FEATS])
    inference_df["prediction"]= total_preds
    inference_df=inference_df.nsmallest(len(inference_df), 'prediction')
    return inference_df["question_id"].tolist()

def get_codingtest_question_df(question_list):
    params="("
    params+=','.join(list(map(str,question_list)))
    params+=")"

    # 데이터 조회 쿼리
    sql_get_question_lastrow = f"""
    WITH
    tmp1 AS (SELECT * FROM `project-modeling.dataset_for_service.new_lgbm_data_inference`
    WHERE question_id in {params}),
    tmp2 AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY question_id) rnk FROM tmp1)
    SELECT * FROM tmp2 WHERE rnk=1
    """

    # 데이터 조회 쿼리 실행 결과
    query_job = client.query(sql_get_question_lastrow)

    # 데이터프레임 변환
    df_codingtest_question = query_job.to_dataframe()
    df_codingtest_question=df_codingtest_question.drop(columns=["rnk"])
    
    return df_codingtest_question

@app.post('/prediction/')
def get_codingtest_prediction(item:prediction_input):
    user_id=item.user_id
    question_list=item.codingtest_question_list
    
    df_codingtest_question=get_codingtest_question_df(question_list)
    my_history_df=get_my_history_df(user_id)
    df_mylastrow=my_history_df.iloc[-1]
    inference_df=pd.DataFrame()
    
    FEATS = ["question_id","level_id",
            "averageTries","lag_time","accuracy_per_question","tag","accuracy_per_tag",
            "cumulated_points","prior_correct_count","prior_count","prior_accuracy","prior_tag_correct_count",
            "prior_tag_count","prior_tag_accuracy"]
    
    for question_id in question_list:
        df_question_mylastrow=df_codingtest_question.loc[df_codingtest_question["question_id"]==question_id].iloc[0]
        df_mytaglastrow=my_history_df.loc[my_history_df["tag"]==df_question_mylastrow.tag]
        lag_time=int(time.time())-df_mylastrow.submitted_epochtime
        
        if df_mytaglastrow.empty==False:
            df_mytaglastrow=df_mytaglastrow.iloc[-1]
            test_row=[df_question_mylastrow.question_id,df_question_mylastrow.level_id,df_question_mylastrow.averageTries,
                lag_time,df_question_mylastrow.accuracy_per_question,df_question_mylastrow.tag,
                df_question_mylastrow.accuracy_per_tag,df_mylastrow.cumulated_points,
                df_mylastrow.prior_correct_count,df_mylastrow.prior_count,df_mylastrow.prior_accuracy,
                df_mytaglastrow.prior_tag_correct_count,df_mytaglastrow.prior_tag_count,
                df_mytaglastrow.prior_tag_accuracy]
        else:
            test_row=[df_question_mylastrow.question_id,df_question_mylastrow.level_id,df_question_mylastrow.averageTries,
                lag_time,df_question_mylastrow.accuracy_per_question,df_question_mylastrow.tag,
                df_question_mylastrow.accuracy_per_tag,df_mylastrow.cumulated_points,
                df_mylastrow.prior_correct_count,df_mylastrow.prior_count,df_mylastrow.prior_accuracy,
                0,0,0]

        one_row=pd.DataFrame([test_row],columns=FEATS)
        inference_df=pd.concat([inference_df,one_row])
    total_preds = model.predict(inference_df[FEATS])
    inference_df["prediction"]= total_preds
    prediction={}
    for i in inference_df[["question_id","prediction"]].values.tolist():
        prediction[int(i[0])]=i[1]

    return prediction

def get_target_questions(user_id,level_id):
    level_id=int(level_id)
    min_level= max(0,level_id-7)
    max_level= min(30,level_id+3)
        

    sql_test = f"""
    WITH
    tmp1 AS (SELECT DISTINCT(question_id) FROM 
    `project-modeling.dataset_for_service.new_lgbm_data_inference` GROUP BY 1),
    tmp2 AS (SELECT problemId question_id,level level_id FROM `project-modeling.dataset_temp.problem_data`
    WHERE {min_level}<=level AND level<={max_level}),
    tmp3 AS (SELECT question_id FROM `project-modeling.dataset_for_train.filtered_question_raw`),
    tmp4 AS (SELECT A.question_id FROM tmp1 A INNER JOIN tmp2 B ON A.question_id=B.question_id)
    SELECT A.question_id FROM tmp3 A INNER JOIN tmp4 B ON A.question_id=B.question_id
    """

    # 데이터 조회 쿼리 실행 결과
    query_job = client.query(sql_test)

    # 데이터프레임 변환
    codingtest_df = query_job.to_dataframe()
    U= codingtest_df["question_id"].tolist()
        
    sql=""
    sql+="SELECT DISTINCT(question_id) FROM learning_history WHERE user_id=@id GROUP BY question_id"
    with database.snapshot() as snapshot:
        A = snapshot.execute_sql(
            sql,
            params={"id": user_id},
            param_types={"id": spanner.param_types.STRING},
        )
    A= list((A))
    A = list(itertools.chain(*list((A))))
    preview_question_list = list(set(U) - set(A))

    return preview_question_list

@app.post('/preview_recommendation/')
def get_preview_recommendation(item:preview_recommendation_input):
    user_id=item.user_id
    level_id=item.level_id
    
    target_questions=get_target_questions(user_id,level_id)
    my_history_df=get_my_history_df(user_id)
    df_mylastrow=my_history_df.iloc[-1]
    df_codingtest_question=get_codingtest_question_df(target_questions)
    inference_df=pd.DataFrame()
    
    FEATS = ["question_id","level_id",
        "averageTries","lag_time","accuracy_per_question","tag","accuracy_per_tag",
        "cumulated_points","prior_correct_count","prior_count","prior_accuracy","prior_tag_correct_count",
        "prior_tag_count","prior_tag_accuracy"]
    
    for question_id in target_questions:
        df_question_mylastrow=df_codingtest_question.loc[df_codingtest_question["question_id"]==question_id].iloc[0]
        df_mytaglastrow=my_history_df.loc[my_history_df["tag"]==df_question_mylastrow.tag]
        lag_time=int(time.time())-df_mylastrow.submitted_epochtime
        if df_mytaglastrow.empty==False:
            df_mytaglastrow=df_mytaglastrow.iloc[-1]
            test_row=[df_question_mylastrow.question_id,df_question_mylastrow.level_id,df_question_mylastrow.averageTries,
                    lag_time,df_question_mylastrow.accuracy_per_question,df_question_mylastrow.tag,
                    df_question_mylastrow.accuracy_per_tag,df_mylastrow.cumulated_points,
                    df_mylastrow.prior_correct_count,df_mylastrow.prior_count,df_mylastrow.prior_accuracy,
                    df_mytaglastrow.prior_tag_correct_count,df_mytaglastrow.prior_tag_count,df_mytaglastrow.prior_tag_accuracy]
        else:
            test_row=[df_question_mylastrow.question_id,df_question_mylastrow.level_id,df_question_mylastrow.averageTries,
                    lag_time,df_question_mylastrow.accuracy_per_question,df_question_mylastrow.tag,
                    df_question_mylastrow.accuracy_per_tag,df_mylastrow.cumulated_points,
                    df_mylastrow.prior_correct_count,df_mylastrow.prior_count,df_mylastrow.prior_accuracy,
                    0,0,0]
        one_row=pd.DataFrame([test_row],columns=FEATS)
        inference_df=pd.concat([inference_df,one_row])
    total_preds = model.predict(inference_df[FEATS])
    inference_df["prediction"]= total_preds
    inference_df["prediction"]= abs((inference_df["prediction"]-0.5))
    
    len_rec=int(min(100,len(inference_df)))
    inference_df=inference_df.nsmallest(len_rec, 'prediction')["question_id"].tolist()

    return inference_df


