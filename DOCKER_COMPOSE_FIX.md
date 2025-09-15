# Docker Compose 命令修复

## 🔧 问题描述

用户报告在使用 `./docker-start.sh` 时出现错误：
```
./docker-start.sh: line 34: docker-compose: command not found
```

这是因为新版本的Docker已经将 `docker-compose` 命令改为 `docker compose`（注意中间的空格）。

## ✅ 修复内容

### 1. 修复的文件

- `docker-start.sh` - 快速启动脚本
- `docker-manage.sh` - Docker管理脚本  
- `test-docker.sh` - Docker配置测试脚本
- `README.md` - 项目文档

### 2. 修复的命令

将所有 `docker-compose` 命令替换为 `docker compose`：

| 原命令 | 新命令 |
|--------|--------|
| `docker-compose build` | `docker compose build` |
| `docker-compose up -d` | `docker compose up -d` |
| `docker-compose down` | `docker compose down` |
| `docker-compose ps` | `docker compose ps` |
| `docker-compose logs` | `docker compose logs` |
| `docker-compose exec` | `docker compose exec` |
| `docker-compose run` | `docker compose run` |
| `docker-compose restart` | `docker compose restart` |
| `docker-compose stop` | `docker compose stop` |
| `docker-compose config` | `docker compose config` |

### 3. 具体修复

#### docker-start.sh
- 修复了构建、启动、状态检查、日志查看等命令
- 更新了帮助信息中的命令示例

#### docker-manage.sh  
- 修复了所有服务管理命令
- 修复了数据操作命令
- 修复了维护操作命令
- 更新了Docker Compose检查逻辑

#### test-docker.sh
- 修复了Docker Compose版本检查
- 修复了配置文件语法检查

#### README.md
- 更新了开发部分的Docker命令示例

## 🎯 兼容性说明

### 新版本Docker (推荐)
- 使用 `docker compose` 命令
- 这是Docker官方推荐的新语法
- 更好的集成和性能

### 旧版本Docker
- 仍支持 `docker-compose` 命令
- 但建议升级到新版本

## 🧪 验证结果

### 语法检查
```bash
bash -n docker-start.sh && bash -n docker-manage.sh && bash -n test-docker.sh
# 结果: 所有脚本语法正确
```

### 功能测试
```bash
./test-docker.sh
# 结果: 脚本正常运行（需要Docker环境）
```

## 📋 使用说明

修复后，所有Docker命令都使用新的语法：

```bash
# 快速启动
./docker-start.sh

# 管理服务
./docker-manage.sh start-web
./docker-manage.sh status
./docker-manage.sh logs

# 测试配置
./test-docker.sh
```

## 🔄 版本要求

- **Docker**: 20.10+
- **Docker Compose**: 2.0+ (使用 `docker compose` 语法)

## ✨ 总结

所有Docker相关脚本已成功更新为新的 `docker compose` 命令语法，确保与新版本Docker的兼容性。用户现在可以正常使用所有Docker管理功能。

---

**🎉 修复完成！现在可以使用 `./docker-start.sh` 正常启动服务了。**
