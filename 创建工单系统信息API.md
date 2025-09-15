# 全局公共参数

**全局Header参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| 暂无参数 |

**全局Query参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| 暂无参数 |

**全局Body参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| 暂无参数 |

**全局认证方式**

> 无需认证

# 状态码说明

| 状态码 | 中文描述 |
| --- | ---- |
| 暂无参数 |

# 创建工单系统信息API

> 创建人: STlxx

> 更新人: STlxx

> 创建时间: 2025-09-08 14:12:44

> 更新时间: 2025-09-09 09:01:01

#### 1. 详细的API功能描述

**此API用于在工单系统中创建相关信息。通过发送POST请求到指定的URL http://192.168.0.54:13000/api/t_d5n8vtsnrwv:create ，携带认证令牌 Authorization 以及特定格式的请求体数据（Content-Type 为 application/json）来完成工单系统信息的创建操作。请求体中包含多个参数，如 id 可能是工单系统信息的唯一标识，其他以 f_ 开头的参数推测为工单系统信息的具体内容，如字符串类型和整数值类型的数据。**

**[object Object],[object Object],[object Object],[object Object],[object Object],[object Object]**

#### 2. 调用API时的注意事项

**认证方面：务必确保 Authorization 令牌的有效性和时效性，过期或错误的令牌将导致认证失败，无法调用API。,数据格式方面：请求体数据必须严格按照 application/json 格式进行组织，每个参数的类型和值需符合预期，否则可能导致服务器解析错误。**

**数据格式方面：请求体数据必须严格按照 application/json 格式进行组织，每个参数的类型和值需符合预期，否则可能导致服务器解析错误。**

**[object Object]**

#### 3. 前端验证建议

**Authorization 令牌：前端可通过简单的字符串格式验证，确保令牌以 Bearer  开头，后续字符符合JWT（JSON Web Token）的基本格式。虽然不建议前端完全验证JWT的有效性（应由后端完成），但可通过正则表达式初步判断格式：/^Bearer\s[\w-]+\.[\w-]+\.[\w-]+$/。,**Content-Type**：前端在发送请求时，确保 Content-Type 头信息设置为 application/json 。,请求体参数：,字符串类型参数：对于像 f_emd69kip4gk、f_ifa9xxyrmft 等字符串类型参数，可根据实际业务需求进行长度限制和字符集验证。例如，如果业务要求字符串只能包含字母和数字，可使用正则表达式 /^[a-zA-Z0-9]+$/。,整数类型参数：对于像 f_iis2qlzmmko、f_4civ803ubaz 等整数类型参数，可验证其是否为有效的整数，可使用JavaScript代码 function isValidInteger(value) { return Number.isInteger(parseFloat(value)) && !isNaN(parseFloat(value)); } 进行验证。**

**[object Object],[object Object],[object Object]**

**请求体参数：
字符串类型参数：对于像 f_emd69kip4gk、f_ifa9xxyrmft 等字符串类型参数，可根据实际业务需求进行长度限制和字符集验证。例如，如果业务要求字符串只能包含字母和数字，可使用正则表达式 /^[a-zA-Z0-9]+$/。
整数类型参数：对于像 f_iis2qlzmmko、f_4civ803ubaz 等整数类型参数，可验证其是否为有效的整数，可使用JavaScript代码 function isValidInteger(value) { return Number.isInteger(parseFloat(value)) && !isNaN(parseFloat(value)); } 进行验证。

**

**字符串类型参数：对于像 f_emd69kip4gk、f_ifa9xxyrmft 等字符串类型参数，可根据实际业务需求进行长度限制和字符集验证。例如，如果业务要求字符串只能包含字母和数字，可使用正则表达式 /^[a-zA-Z0-9]+$/。,整数类型参数：对于像 f_iis2qlzmmko、f_4civ803ubaz 等整数类型参数，可验证其是否为有效的整数，可使用JavaScript代码 function isValidInteger(value) { return Number.isInteger(parseFloat(value)) && !isNaN(parseFloat(value)); } 进行验证。**

**[object Object],[object Object]**

**整数类型参数：对于像 f_iis2qlzmmko、f_4civ803ubaz 等整数类型参数，可验证其是否为有效的整数，可使用JavaScript代码 function isValidInteger(value) { return Number.isInteger(parseFloat(value)) && !isNaN(parseFloat(value)); } 进行验证。**

**[object Object],[object Object],[object Object]**

**接口状态**

> 开发中

**接口URL**

> http://192.168.0.54:13000/api/t_d5n8vtsnrwv:create

**请求方式**

> POST

**Content-Type**

> json

**请求Header参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| Authorization | Bearer  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsInJvbGVOYW1lIjoiYWRtaW4iLCJpYXQiOjE3NTU4Mzk3NTcsImV4cCI6MzMzMTM0Mzk3NTd9.4xYz71zgKO2S_iluTwCY7i2h1nRpHE1cuMKa20E7grw | string | 是 | 认证令牌 |
| Content-Type | application/json | string | 是 | 请求体的数据类型 |

**请求Body参数**

```javascript
{
  "id":"1",//编号
  "f_emd69kip4gk": "string", //编号
  "f_ifa9xxyrmft": "string", //项目名称
  "f_jxzzjg7egqm": "string", //项目申请人
  "f_utqw1679w43": "string", //状态
  "f_iis2qlzmmko": 0, //开始时间-时间戳
  "f_4civ803ubaz": 0, //结束时间-时间戳
  "f_8ufkn1d1z3v": 0, //摄影师开始时间-时间戳
  "f_augkx557xwf": 0, //摄影师结束时间-时间戳
  "f_vyp0iizeom5": 0, //美工开始时间-时间戳
  "f_pkcr94xo1py": 0, //美工结束时间-时间戳
  "f_n9vu52g0c4f": 0, //剪辑开始时间-时间戳
  "f_6aocwxxqcfj": 0  //剪辑结束时间-时间戳
}
```

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| id | 1 | string | 是 | 编号 |
| f_emd69kip4gk | string | string | 是 | 编号 |
| f_ifa9xxyrmft | string | string | 是 | 项目名称 |
| f_jxzzjg7egqm | string | string | 是 | 项目申请人 |
| f_utqw1679w43 | string | string | 是 | 状态 |
| f_iis2qlzmmko | 0 | number | 是 | 开始时间-时间戳 |
| f_4civ803ubaz | 0 | number | 是 | 结束时间-时间戳 |
| f_8ufkn1d1z3v | 0 | number | 是 | 摄影师开始时间-时间戳 |
| f_augkx557xwf | 0 | number | 是 | 摄影师结束时间-时间戳 |
| f_vyp0iizeom5 | 0 | number | 是 | 美工开始时间-时间戳 |
| f_pkcr94xo1py | 0 | number | 是 | 美工结束时间-时间戳 |
| f_n9vu52g0c4f | 0 | number | 是 | 剪辑开始时间-时间戳 |
| f_6aocwxxqcfj | 0 | number | 是 | 剪辑结束时间-时间戳 |

**认证方式**

> 继承父级

**响应示例**

* 成功(200)

```javascript
暂无数据
```

* 失败(404)

```javascript
暂无数据
```

**请求Header参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| Authorization | Bearer  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsInJvbGVOYW1lIjoiYWRtaW4iLCJpYXQiOjE3NTU4Mzk3NTcsImV4cCI6MzMzMTM0Mzk3NTd9.4xYz71zgKO2S_iluTwCY7i2h1nRpHE1cuMKa20E7grw | string | 是 | 认证令牌 |
| Content-Type | application/json | string | 是 | 请求体的数据类型 |

**Query**
