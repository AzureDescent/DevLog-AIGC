# [关键修改] 使用 python:3.11-slim-bookworm 锁定为 Debian 12 稳定版
# 这样才能完美匹配下面的 prince_15.3-1_debian12 安装包
FROM python:3.11-slim-bookworm

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 & PrinceXML
RUN apt-get update && \
    # 安装基础工具和 Prince 的依赖库
    apt-get install -y git curl gdebi-core libxml2 libgomp1 fonts-stix && \
    # 下载 PrinceXML (Debian 12 专用版)
    curl -O https://www.princexml.com/download/prince_15.3-1_debian12_amd64.deb && \
    # 使用 gdebi 安装 (它会自动解决剩余依赖)
    gdebi --n prince_15.3-1_debian12_amd64.deb && \
    # 清理安装包和缓存，减小镜像体积
    rm prince_15.3-1_debian12_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目代码
COPY . .

# 6. 启动命令
ENTRYPOINT ["python", "GitReport.py"]