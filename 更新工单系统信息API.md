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

# 更新工单系统信息API

> 创建人: STlxx

> 更新人: STlxx

> 创建时间: 2025-09-09 08:55:48

> 更新时间: 2025-09-09 09:06:40

#### 1. API 功能详细描述

**此 API 用于更新工单系统的相关信息。通过 POST 请求方式，携带特定的请求参数到指定的 URL 地址，实现对工单系统数据的更新操作。**

**[object Object]**

**请求参数：,header 参数：,**Authorization**：认证令牌，用于验证请求的合法性，确保只有授权用户能够访问该 API。格式为 Bearer <token>，其中 <token> 是经过加密生成的 JWT 令牌。,**Content-Type**：指定请求体的数据类型为 application/json，表明请求体数据以 JSON 格式进行传输。,,,query 参数：,**filterByTk**：编号，用于筛选需要更新的工单系统信息，值为字符串类型。,,,body 参数：,**f_emd69kip4gk**：可能是某个编号或数值，值为字符串类型。,**f_ifa9xxyrmft**：可能是某种字符串标识，值为字符串类型。,**f_jxzzjg7egqm**：可能是某种字符串标识，值为字符串类型。,**f_utqw1679w43**：可能是某种字符串标识，值为字符串类型。,**f_iis2qlzmmko**：可能是某个状态值或计数初始值，值为整数类型。,**f_4civ803ubaz**：可能是某个状态值或计数初始值，值为整数类型。,**f_8ufkn1d1z3v**：可能是某个状态值或计数初始值，值为整数类型。,**f_augkx557xwf**：可能是某个状态值或计数初始值，值为整数类型。,**f_vyp0iizeom5**：可能是某个状态值或计数初始值，值为整数类型。,**f_pkcr94xo1py**：可能是某个状态值或计数初始值，值为整数类型。,**f_n9vu52g0c4f**：可能是某个状态值或计数初始值，值为整数类型。,**f_6aocwxxqcfj**：可能是某个状态值或计数初始值，值为整数类型。,,,,,业务逻辑：根据 filterByTk 筛选出对应的工单系统信息，然后使用 body 中的参数对筛选出的信息进行更新。**

****f_iis2qlzmmko**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_4civ803ubaz**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_8ufkn1d1z3v**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_augkx557xwf**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_vyp0iizeom5**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_pkcr94xo1py**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_n9vu52g0c4f**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

****f_6aocwxxqcfj**：可能是某个状态值或计数初始值，值为整数类型。**

**[object Object]**

**业务逻辑：根据 filterByTk 筛选出对应的工单系统信息，然后使用 body 中的参数对筛选出的信息进行更新。**

**[object Object],[object Object]**

#### 2. 调用 API 时的注意事项

**认证方面：确保 Authorization 令牌的有效性和时效性，过期的令牌将导致请求失败。建议在令牌即将过期时提前进行刷新操作。,参数方面：,确保 Content-Type 为 application/json，否则服务器可能无法正确解析请求体数据。,对于 filterByTk，要保证其值符合工单系统中编号的实际格式和规则，避免因编号错误导致无法准确筛选到需要更新的信息。,对于 body 中的各个参数，要根据实际业务需求准确赋值，避免因参数值错误导致更新数据出现偏差。**

**[object Object],[object Object]**

**对于 filterByTk，要保证其值符合工单系统中编号的实际格式和规则，避免因编号错误导致无法准确筛选到需要更新的信息。**

**[object Object]**

**对于 body 中的各个参数，要根据实际业务需求准确赋值，避免因参数值错误导致更新数据出现偏差。**

**[object Object]**

#### 3. 前端验证建议

****Authorization**：前端可以通过正则表达式验证令牌格式是否为 Bearer <token>，示例正则表达式：/^Bearer\s+\S+$/。,**filterByTk**：由于其为字符串类型，前端可以根据工单系统编号的实际规则进行验证，例如如果编号为数字组成且长度固定为 4 位，正则表达式可以为：/^\d{4}$/。,body 中的参数：,对于字符串类型的参数（f_emd69kip4gk、f_ifa9xxyrmft、f_jxzzjg7egqm、f_utqw1679w43），可以根据实际业务需求验证其长度、字符集等。例如，如果要求只能是字母和数字组成且长度不超过 20 位，正则表达式可以为：/^[a-zA-Z0-9]{0,20}$/。,对于整数类型的参数（f_iis2qlzmmko、f_4civ803ubaz、f_8ufkn1d1z3v、f_augkx557xwf、f_vyp0iizeom5、f_pkcr94xo1py、f_n9vu52g0c4f、f_6aocwxxqcfj），可以验证其是否为有效的整数，正则表达式可以为：/^-?\d+$/。**

**[object Object],[object Object]**

**body 中的参数：
对于字符串类型的参数（f_emd69kip4gk、f_ifa9xxyrmft、f_jxzzjg7egqm、f_utqw1679w43），可以根据实际业务需求验证其长度、字符集等。例如，如果要求只能是字母和数字组成且长度不超过 20 位，正则表达式可以为：/^[a-zA-Z0-9]{0,20}$/。
对于整数类型的参数（f_iis2qlzmmko、f_4civ803ubaz、f_8ufkn1d1z3v、f_augkx557xwf、f_vyp0iizeom5、f_pkcr94xo1py、f_n9vu52g0c4f、f_6aocwxxqcfj），可以验证其是否为有效的整数，正则表达式可以为：/^-?\d+$/。

**

**[object Object]**

**对于字符串类型的参数（f_emd69kip4gk、f_ifa9xxyrmft、f_jxzzjg7egqm、f_utqw1679w43），可以根据实际业务需求验证其长度、字符集等。例如，如果要求只能是字母和数字组成且长度不超过 20 位，正则表达式可以为：/^[a-zA-Z0-9]{0,20}$/。,对于整数类型的参数（f_iis2qlzmmko、f_4civ803ubaz、f_8ufkn1d1z3v、f_augkx557xwf、f_vyp0iizeom5、f_pkcr94xo1py、f_n9vu52g0c4f、f_6aocwxxqcfj），可以验证其是否为有效的整数，正则表达式可以为：/^-?\d+$/。**

**[object Object],[object Object],[object Object],[object Object]**

**对于整数类型的参数（f_iis2qlzmmko、f_4civ803ubaz、f_8ufkn1d1z3v、f_augkx557xwf、f_vyp0iizeom5、f_pkcr94xo1py、f_n9vu52g0c4f、f_6aocwxxqcfj），可以验证其是否为有效的整数，正则表达式可以为：/^-?\d+$/。**

**[object Object],[object Object],[object Object],[object Object],[object Object],[object Object],[object Object],[object Object],[object Object]**

**接口状态**

> 开发中

**接口URL**

> http://192.168.0.54:13000/api/t_d5n8vtsnrwv:update?filterByTk=4

**请求方式**

> POST

**Content-Type**

> json

**请求Header参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| Authorization | Bearer  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsInJvbGVOYW1lIjoiYWRtaW4iLCJpYXQiOjE3NTU4Mzk3NTcsImV4cCI6MzMzMTM0Mzk3NTd9.4xYz71zgKO2S_iluTwCY7i2h1nRpHE1cuMKa20E7grw | string | 是 | 认证令牌 |
| Content-Type | application/json | string | 是 | 请求体的数据类型 |

**请求Query参数**

| 参数名 | 示例值 | 参数类型 | 是否必填 | 参数描述 |
| --- | --- | ---- | ---- | ---- |
| filterByTk | 4 | string | 是 | //编号 |

**请求Body参数**

```javascript
{
  "f_emd69kip4gk": "2", //编号
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
| f_emd69kip4gk | 2 | string | 是 | 编号 |
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
