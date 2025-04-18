# 牛客-气球发放管理工具

这是一个基于`Flask`的实时气球发放管理系统，专为牛客平台在线编程竞赛设计。系统能高效地管理和追踪比赛中选手解题后的气球发放流程，提升志愿者工作效率。
在`ACM/ICPC`等程序设计竞赛中，当选手成功解答一道题目时，志愿者需要为其送上相应颜色的气球，本系统就是为了更好地管理这个过程而设计的。

## 功能特点

- 实时获取比赛提交状态
- 自动记录并追踪气球发放状态
- 支持多区域气球发放管理
- 提供气球颜色配置功能
- 实时刷新和状态更新
- 支持按区域和发放状态筛选
- 数据本地持久化存储

## 技术栈

- 后端：Flask 
- 前端：原生HTML/CSS/JavaScript
- 数据存储：CSV文件
- 依赖：requests 

## 安装部署

1. 克隆项目到本地

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置气球颜色
在`balloon_color.csv`文件中配置每道题目对应的气球颜色，格式如下：
```csv
problemId,balloonColor,hexColor
A,红色,#FF0000
B,蓝色,#0000FF
```

4. 启动服务
```bash
python app.py
```

## 使用说明

1. 访问系统
   - 启动服务后，访问 http://localhost:5173

2. 输入比赛信息
   - 在页面顶部输入比赛ID
   - 设置自动刷新间隔（默认60秒）

3. 气球发放管理
   - 使用区域筛选器选择特定区域
   - 使用状态筛选器查看已发放/未发放气球
   - 点击对应记录可更新气球发放状态

4. 数据存储
   - 系统会自动为每场比赛创建独立的CSV文件存储提交记录和气球发放状态
   - 文件命名格式：`{contestId}_res.csv`

5. 参赛选手信息配置
   - 在`a.csv`文件中配置参赛选手的信息，格式如下：
   ```csv
   userId,userName,area,address
   ```
   - 字段说明：
     - userId：牛客的用户id
     - userName：牛客的用户名
     - area：选手所在区域（如A区、B区等）
     - address：选手的座位信息（如3排1座）
   - 示例：
   ```csv
   423420588,牛客423420588号,A区,3排1座
   ```
   - 确保所有选手信息正确填写，系统将根据这些信息进行气球发放管理

## 数据关联关系

系统中的CSV文件之间存在以下关联关系：

1. 参赛选手信息文件（a.csv）与比赛结果文件（{contestId}_res.csv）
   - 通过用户ID（userId）关联，实现选手信息与提交记录的映射
   - 当系统获取到新的提交记录时，会根据用户ID自动查找a.csv中对应的选手信息
   - 这种关联使得系统能够实时显示选手的区域和座位信息，方便志愿者准确送达气球
   - 如果用户ID在a.csv中不存在，系统会显示"未知区域"和"未知座位"

2. 气球颜色配置文件（balloon_color.csv）与比赛结果文件
   - 通过题目ID（problemId）关联，确保每道题目对应固定的气球颜色
   - 系统会根据提交记录中的题目ID，自动匹配balloon_color.csv中配置的气球颜色和十六进制颜色值
   - 这种关联确保了气球颜色的一致性，并在界面上以对应的颜色直观显示
   - 气球颜色配置支持动态更新，修改balloon_color.csv后即时生效
   - 数据流转过程
   - 系统定期从比赛平台获取新的AC（Accepted）提交记录
   - 对每条新记录，系统首先根据用户ID关联查找选手信息（区域和座位）
   - 同时根据题目ID关联查找对应的气球颜色信息
   - 将这些信息整合后保存到比赛结果文件（{contestId}_res.csv）中
   - 比赛结果文件会记录每个气球的发放状态（given/not_given）
   - 所有信息最终在前端界面集中展示，支持按区域筛选和状态筛选
   - 志愿者可以通过界面快速切换气球发放状态，系统会自动更新到结果文件中

## 注意事项

- 确保系统运行时有正确的文件读写权限
- 建议定期备份数据文件
- 使用前请正确配置气球颜色信息