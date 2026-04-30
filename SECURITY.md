# Security Policy

## Supported Versions
当前仅维护 `main` 分支的最新版本。

## Reporting a Vulnerability
请不要在公开 Issue 中披露安全漏洞。

请通过以下方式私下报告：
- 优先使用仓库的私密安全报告（Security Advisories）。
- 若仓库维护者已提供安全邮箱，请使用真实邮箱；不要使用占位邮箱。

提交报告时请包含：
- 漏洞描述与影响范围
- 复现步骤或 PoC
- 受影响版本与环境信息
- 修复建议（可选）

我们会在 72 小时内确认收到，并尽快评估与修复。

## Disclosure Policy

- 在修复发布前，请不要公开披露漏洞细节。
- 维护者确认修复后，可在公告中致谢报告者（如报告者同意）。

## Security Best Practices

- 禁止在仓库中提交明文密码、API 密钥、Webhook、证书私钥。
- 生产环境建议使用最小权限数据库账号。
- 建议在发布前进行依赖与配置的安全检查。
