from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import time
import logging
import csv
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 存储气球状态的数据结构
balloon_status = {}

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

@app.route('/balloon')
def balloon():
    return render_template('balloon.html')

@app.route('/res.csv')
def get_res_csv():
    try:
        with open('res.csv', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return str(e), 500

@app.route('/a.csv')
def get_a_csv():
    try:
        with open('a.csv', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return str(e), 500

@app.route('/api/data')
def get_data():
    # 从查询参数中获取比赛ID和状态过滤器
    contest_id = request.args.get('contestId', '104226')
    # status_type_filter = request.args.get('statusTypeFilter')
    status_type_filter = 5
    
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
    
    # 将数据保存到res.csv文件
    try:
        # 读取已有数据的最后一条记录时间
        last_submit_time = None
        try:
            with open('res.csv', 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                # 如果文件存在但为空，或者没有有效数据行，last_submit_time保持为None
                if rows:
                    last_submit_time = datetime.strptime(rows[-1]['submitTime'], '%Y-%m-%d %H:%M:%S')
        except FileNotFoundError:
            # 如果文件不存在，创建文件并写入表头
            with open('res.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
                writer.writeheader()

        # 追加写入新数据
        with open('res.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
            for item in unique_data:
                current_time = datetime.strptime(item['submitTime'], '%Y-%m-%d %H:%M:%S')
                # 只写入时间在最后一条记录之后的数据
                if last_submit_time is None or current_time > last_submit_time:
                    writer.writerow({
                        'userId': item['userId'],
                        'userName': item['userName'],
                        'problemId': item['index'],
                        'submitTime': item['submitTime'],
                        'balloonStatus': 'not_given'
                    })
        logger.info('数据已成功追加保存到res.csv文件')
    except Exception as e:
        logger.error(f'保存数据到res.csv失败: {str(e)}')
    
    return jsonify(unique_data)

@app.route('/balloon/status', methods=['POST'])
def update_balloon_status():
    data = request.json
    user_id = data.get('userId')
    problem_id = data.get('problemId')
    is_given = data.get('isGiven')
    
    if not all([user_id, problem_id, isinstance(is_given, bool)]):
        return jsonify({'error': '参数不完整'}), 400
    
    key = f"{user_id}_{problem_id}"
    balloon_status[key] = {
        'isGiven': is_given,
        'updateTime': datetime.now().isoformat()
    }
    
    # 更新res.csv文件中的气球状态
    try:
        rows = []
        with open('res.csv', 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        for row in rows:
            if row['userId'] == user_id and row['problemId'] == problem_id:
                row['balloonStatus'] = 'given' if is_given else 'not_given'
        
        with open('res.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        logger.error(f'更新气球状态失败: {str(e)}')
        return jsonify({'error': '更新气球状态失败'}), 500
    
    return jsonify({'success': True})

@app.route('/balloon/status', methods=['GET'])
def get_balloon_status():
    return jsonify(balloon_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5173, debug=True)