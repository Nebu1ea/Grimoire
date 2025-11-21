# Grimoire
苦逼牛马的毕业设计

## 通信协议

### 通信加密流程
设计把 任务输出 先base64为 output字段, 然后格式化成整个payload:

```
{
    "task_id":id,
    "output": output
}
```

然后把这个payload进行以下加密:

AESGCM -> 头部加上IV,尾部加上 beacon_id,具体为 IV | CT | TAG | SF ->base64

最后伪装到 auth 字段中：

```
{
    "auth":加密后payload,
    "question":随机question,
    "user":user
}
```

而server返回任务的时候格式为:

```
{
    "task_id":task_id,
    "command":任务种类,
    "argument":任务参数
}
```

按照同样的加密方式加密，最后伪装到 X-DATA-REF 头里面。

```
X-DATA-REF: 加密payload
{
    "answer":answer
}
```

### 握手流程
beacon发送

```
{
    "hello":公钥,
    "user":beacon读出来的用户名,
    "password":随便
}
```

server发送

```
{
    "welcome":公钥,
    "user":beacon读出来的用户名,
    "info":"welcome for chat"
}
```

算法用对方的公钥和自己的密钥派生出AESGCM共享密钥。

再用AESGCM共享密钥派生出beacon_id

这样就一次握手全部解决完了。