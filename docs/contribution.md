# 贡献提PR流程

### 1. Fork仓库

打开Github项目主页`https://github.com/FlandreSatori/calabiyau-workshop-pixelart`，`Fork`到自己账号。

### 2. 拉取代码&配置远程

```powershell
# 拉取原仓库代码
git clone https://github.com/FlandreSatori/calabiyau-workshop-pixelart.git
cd calabiyau-workshop-pixelart

# 绑定自己fork仓库（替换为你的仓库地址）
git remote add myfork https://github.com/<USERNAME>/calabiyau-workshop-pixelart.git

# 查看远程是否配置成功
git remote -v
```

> origin=原项目仓库；myfork=你的个人仓库

### 3. 修改后本地提交

```powershell
git add .
# 规范提交备注：feat/fix/docs: 改动简述
git commit -m "feat: 改动描述"
```

### 4. 推送至自己仓库

```powershell
# 只推myfork
git push myfork main
```

### 5. 网页提PR

打开你的Github仓库 → 点击`Open a pull request`

- Base：`FlandreSatori/calabiyau-workshop-pixelart:main`
- Compare：`你的账号/calabiyau-workshop-pixelart:main`
  填写标题和改动说明，创建PR等待审核。

---

如有疑问或问题，欢迎留言交流，本项目的完善有赖于每一位开发者的参与和贡献喵！