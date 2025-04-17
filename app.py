from math import log
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
    
    # 读取对应contestId的CSV文件中的现有数据
    existing_data = {}
    csv_filename = f'{contest_id}_res.csv'
    try:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['userId']}_{row['problemId']}"
                existing_time = datetime.strptime(row['submitTime'], '%Y-%m-%d %H:%M:%S')
                if key not in existing_data or existing_time > datetime.strptime(existing_data[key]['submitTime'], '%Y-%m-%d %H:%M:%S'):
                    existing_data[key] = row
    except FileNotFoundError:
        logger.info(f'{csv_filename}文件不存在，创建新文件并写入表头')
        # 如果文件不存在，创建文件并写入表头
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
            writer.writeheader()
        return jsonify([])
    
    # 合并新数据和现有数据，保留最新的提交记录
    merged_data = existing_data.copy()
    for item in unique_data:
        key = f"{item['userId']}_{item['index']}"
        current_time = datetime.strptime(item['submitTime'], '%Y-%m-%d %H:%M:%S')
        
        if key not in merged_data or current_time > datetime.strptime(merged_data[key]['submitTime'], '%Y-%m-%d %H:%M:%S'):
            merged_data[key] = {
                'userId': item['userId'],
                'userName': item['userName'],
                'problemId': item['index'],
                'submitTime': item['submitTime'],
                'balloonStatus': merged_data.get(key, {}).get('balloonStatus', 'not_given')
            }
    
    # 将合并后的数据写入对应contestId的CSV文件
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
            writer.writeheader()
            writer.writerows(merged_data.values())
        logger.info(f'数据已成功保存到{csv_filename}文件')
    except Exception as e:
        logger.error(f'保存数据到{csv_filename}失败: {str(e)}')
    
    # 返回最新的数据
    return jsonify(list(merged_data.values()))

@app.route('/api/balloon-colors')
def get_balloon_colors():
    try:
        colors = {}
        with open('balloon_color.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                colors[row['problemId']] = {
                    'balloonColor': row['balloonColor'],
                    'hexColor': row['hexColor']
                }
        return jsonify(colors)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    
    # 从请求中获取contestId
    contest_id = data.get('contestId')
    if not contest_id:
        return jsonify({'error': '缺少contestId参数'}), 400
        
    csv_filename = f'{contest_id}_res.csv'
    
    # 更新对应contestId的CSV文件中的气球状态
    try:
        rows = []
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        for row in rows:
            if row['userId'] == user_id and row['problemId'] == problem_id:
                row['balloonStatus'] = 'given' if is_given else 'not_given'
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['userId', 'userName', 'problemId', 'submitTime', 'balloonStatus'])
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        logger.error(f'更新气球状态失败: {str(e)}')
        return jsonify({'error': '更新气球状态失败'}), 500
    
    return jsonify({'success': True})

@app.route('/balloon/status', methods=['GET'])
def get_balloon_status():
    contest_id = request.args.get('contestId')
    if not contest_id:
        return jsonify({'error': '缺少contestId参数'}), 400
        
    csv_filename = f'{contest_id}_res.csv'
    try:
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['userId']}_{row['problemId']}"
                balloon_status[key] = {
                    'isGiven': row['balloonStatus'] == 'given',
                    'updateTime': datetime.now().isoformat()
                }
    except FileNotFoundError:
        logger.info(f'{csv_filename}文件不存在，所有气球状态默认为未发放')
    
    return jsonify(balloon_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5173, debug=True)