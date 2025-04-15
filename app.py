from flask import Flask, render_template, jsonify
import requests
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def fetch_data():
    """从API获取数据并处理"""
    try:
        url = 'https://ac.nowcoder.com/acm-heavy/acm/contest/status-list'
        params = {
            'id': '104226',
            'page': '1',
            'pageSize': '50',
            'statusCount': '200',
            'statusTypeFilter':5,
            'searchUserName': '',
            '_': int(time.time() * 1000)
        }
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://ac.nowcoder.com',
            'Referer': 'https://ac.nowcoder.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        
        logger.info(f'API响应状态码: {data.get("code")}, 消息: {data.get("data")}')
        
        if data['code'] != 0:
            raise Exception(f"API error! message: {data['msg']}")
        
        result_data = data['data']['data']
        logger.info(f'成功获取数据，返回{len(result_data)}条记录')
        return result_data
    except Exception as error:
        logger.error(f'获取数据失败: {str(error)}')
        return []

def remove_duplicates(data):
    """根据id和userId去重"""
    unique_data = []
    seen = set()
    
    for item in data:
        key = f"{item['index']}-{item['userId']}"
        if key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    return unique_data

def format_date(timestamp):
    """格式化时间戳为可读日期"""
    return datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    data = fetch_data()
    unique_data = remove_duplicates(data)
    
    # 格式化时间
    for item in unique_data:
        item['submitTime'] = format_date(item['submitTime'])
    
    return jsonify(unique_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5173, debug=True)