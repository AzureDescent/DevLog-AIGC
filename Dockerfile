# 1. 基础镜像：使用官方精简版 Python 3.11
FROM python:3.11-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 安装系统依赖：您的 git_utils.py 需要 git 命令
#    V4.0+ 版本还需安装 prince (用于PDF生成)，这里我们先装 git 确保基础功能
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean

# 4. 复制依赖清单并安装 Python 库
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目所有代码到容器中
COPY . .

# 6. 设置容器启动时的默认命令
ENTRYPOINT ["python", "GitReport.py"]