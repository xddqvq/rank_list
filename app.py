from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# def fetch_data(contest_id='104226', status_type_filter=5):
def fetch_data(contest_id, status_type_filter):
    """从API获取数据并处理
    Args:
        contest_id (str): 比赛ID
        status_type_filter (int): 状态过滤器
    Returns:
        list: 所有提交记录数据
    """
    all_data = []
    page = 1
    page_size = 50
    pageCount = None
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://ac.nowcoder.com',
        'Referer': 'https://ac.nowcoder.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    try:
        while pageCount is None or page <= pageCount:
            url = 'https://ac.nowcoder.com/acm-heavy/acm/contest/status-list'
            params = {
                'id': contest_id,
                'page': str(page),
                'pageSize': str(page_size),
                'searchUserName': '',
                '_': int(time.time() * 1000)
            }
            
            # 只有当status_type_filter有值时才添加到请求参数中
            if status_type_filter is not None:
                params['statusTypeFilter'] = status_type_filter
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != 0:
                raise Exception(f"API error! message: {data['msg']}")
            
            # 获取全量数据
            if pageCount is None:
                basic_info = data['data'].get('basicInfo', {})
                logger.info(f'获取基本信息: {basic_info}')
                pageCount = (int)(basic_info.get('pageCount')) # 总页数
                total_info = (int)(basic_info.get('pageSize')) * pageCount # 总记录数
                logger.info(f'总记录数: {total_info}, 总页数: {pageCount}')
            
            result_data = data['data']['data']
            all_data.extend(result_data)
            logger.info(f'成功获取第{page}页数据，返回{len(result_data)}条记录')
            
            page += 1
            
        logger.info(f'所有数据获取完成，共{len(all_data)}条记录')
        return all_data
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
    # 从查询参数中获取比赛ID和状态过滤器
    contest_id = request.args.get('contestId', '104226')
    status_type_filter = request.args.get('statusTypeFilter')
    
    # 只有当statusTypeFilter有值时才转换为整数
    if status_type_filter is not None:
        try:
            status_type_filter = int(status_type_filter)
        except (ValueError, TypeError):
            status_type_filter = None
    
    data = fetch_data(contest_id, status_type_filter)
    unique_data = remove_duplicates(data)
    
    # 格式化时间
    for item in unique_data:
        item['submitTime'] = format_date(item['submitTime'])
    
    return jsonify(unique_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5173, debug=True)