---
title: "蓝牙协议分析(10)_BLE安全机制之LE Encryption"
date: 2017-03-28T11:52:27+08:00
url: "/bluetooth/le_encryption.html"
gid: "388"
emlog_type: "blog"
summary: "前面文章介绍了两种BLE的安全机制：白名单 [4] 和LL privacy [3] 。说实话，在这危机四伏的年代，这两种“捂着脸讲话（其它人不知道是谁在讲话，因而不能插话、不能假传圣旨，但讲话的内容却听得一清二楚）”的方法，实在是小儿科。对于物联网的应用场景来说，要做到安全，就必须对传输的数据进行加密，这就是LE Encryption要完成的事情（当然，只针对面向连接的数据），具体请参考本文的介绍"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "BLE", "安全", "Encryption"]
views: 44926
comment_count: 30
aliases:
  - "/bluetooth/388.html"
  - "/388.html"
---

## 1. 前言

前面文章介绍了两种BLE的安全机制：白名单[4]和LL privacy[3]。说实话，在这危机四伏的年代，这两种“捂着脸讲话（其它人不知道是谁在讲话，因而不能插话、不能假传圣旨，但讲话的内容却听得一清二楚）”的方法，实在是小儿科。对于物联网的应用场景来说，要做到安全，就必须对传输的数据进行加密，这就是LE Encryption要完成的事情（当然，只针对面向连接的数据），具体请参考本文的介绍。

## 2. 基本概念

从字面理解，Encryption是一个名词，意思是“加密术”，因此LE Encryption就是“BLE所使用的加密技术”的意思。了解加密概念的同学应该都知道，通信过程中的加密无非就是如下简单的流程：

> 数据发送方在需要发送数据的时候，按照一定的加密算法，将数据加密；
>
> 数据接收方在接收到数据的时候，按照等同的解密算法，将数据解密。

因此，对LE Encryption来说，需要考虑的事情无非就两条：

> 1）加密/解密的事情，需要在协议的哪个层次去做？
>
> 2）使用什么样的加密/解密算法？

对问题1来说，很好回答：无论是从安全的角度，还是从通信效率的角度，都应该由链路层（LL，Link Layer[1]）在发送/接收数据的时候，完成加密/解密动作（具体可参考）。而问题2呢，到底要使用什么的算法，这是蓝牙标准化组织的事情，我们在本文只需要了解最终的结论即可（具体可参考）。

## 3. packet的加密/解密过程

LE加密/解密的过程如下面图片1所示：

[![LE加密解密](/content/uploadfile/201703/e7b0bba362d92ccda866ce74cffcada720170328035225.gif "LE加密解密")](/content/uploadfile/201703/fb35af6a4e96b398c26682018083d25a20170328035225.gif)

图片1 LE加密/解密过程

> Master/Slave的LE Host会保存一个LTK（Long Term Key，至少128bits），对BLE用户（或者应用）来说，这个Key是所有加密/解密动作源头；
>
> 每当为某个LE连接启动加密传输的时候，Master和Slave的LL会协商生成一个128bits的随机数SKD（Session Key Diversifier，128bits），并以它为输入，以LTK为key，通过Encryption Engine加密生成SessionKey；
>
> 每当有明文数据包需要发送的时候，需要对明文进行加密。加密的过程，是以明文数据包为输入，以SessionKey为Key，同样通过Encryption Engine加密生成密文数据包；
>
> 同样，每当收到密文数据包的时候，需要对密文解密。解密的过程，是以密文数据包为输入，以SessionKey为Key，同样通过Encryption Engine解密生成明文数据包。

理解了加密/解密的过程之后，问题随之而来：

1）LTK是怎么来的？

2）SKD是个什么东西？怎么来的？

3）Encryption Engine又什么东西呢？

对于问题1，需要由SMP解答（也就是我们常说的配对过程），具体可参考后续的文章。问题3比较单纯，就是一个由Bluetooth specifiction所规定的加密算法，后面会单独写一篇文章介绍。而问题2，则涉及到LE Encryption的操作流程，具体可参考后面第4章的介绍。

## 4. Encryption Procedure

LE Encryption的过程主要由Link Layer控制（具体可参考“BLUETOOTH SPECIFICATION Version 4.2 [Vol 6, Part B] 5.1.3 Encryption Procedure”）：当连接建立之后，Link Layer可以应Host的请求，使能对数据包的Encryption操作，过程如下（具体可参考“BLUETOOTH SPECIFICATION Version 4.2 [Vol 6, Part D] 6.6 START ENCRYPTION”）：

[![LE encryption](/content/uploadfile/201703/0a35e18ba0960f0f8e6468123668b5ab20170328035226.gif "LE encryption")](/content/uploadfile/201703/77a80593c0ea43f0ed5d3ee944b0365320170328035226.gif)

图片2 Start Encryption

1）Host A发送LE Start Encryption HCI命令，请求Link Layer启动加密。该命令的格式如下：

> |  |  |  |  |
> | --- | --- | --- | --- |
> | Command | OCF | Command parameters | Return Parameters |
> | HCI\_LE\_Start\_Encryption | 0x0019 | Connection\_Handle    Random\_Number    Encrypted\_Diversifier    Long\_Term\_Key |  |
>
> Connection\_Handle，连接句柄；   
> Random\_Number和Encrypted\_Diversifier分别简称为Rand和EDIV（Rand是一个64bits的随机数，EDIV是一个16bits的Diversifier），它们在LE Legacy Pairing的过程中，用于在多个LTK标识某一个具体的LTK。而在新的LE Secure Connections Pairing过程中，则不再使用（赋值为0即可）。关于LE的配对过程，可参考后面SMP的分析文章，这里不再详细描述；   
> Long\_Term\_Key，保存在Host段的加密key。

2）LL A收到Host的加密请求之后，会向LL B发送LL\_ENC\_REQ PDU以请求加密，该PDU的格式为：

> |  |  |  |  |
> | --- | --- | --- | --- |
> | Rand (8 octets) | EDIV (2 octets) | SKDm (8 octets) | IVm (4 octets) |
>
> Rand和EDIV就是上面的Random\_Number和Encrypted\_Diversifier；   
> SKDm（session key diversifier ），是一个64bits的随机数，用于和SKDs一起，生成本次加密的SessionKey；   
> IVm（initialization vector ），一个32bits的随机数，和IVs一起组成64bits的IV，后面Encryption Engine会使用。

3）LL B收到LL\_ENC\_REQ PDU之后，会向Host B发送LE Long Term Key Request HCI Event，该Event的格式为：

> |  |  |  |
> | --- | --- | --- |
> | Event | Event code | Event Parameters |
> | LE Long Term Key Request | 0x3E | Subevent\_Code    Connection\_Handle    Random\_Number    Encryption\_Diversifier |
>
> Subevent\_Code为0x05；   
> Connection\_Handle，连接句柄；   
> Random\_Number和Encrypted\_Diversifier就是LL\_ENC\_REQ PDU中的Rand和EDIV，最初是由Host A通过LE Start Encryption命令发送过来的。

4）如果Host B能提供LTK，则通过LE Long Term Key Request Reply HCI命令，将LTK提供给LL B，该命令的格式为：

> |  |  |  |  |
> | --- | --- | --- | --- |
> | Command | OCF | Command parameters | Return Parameters |
> | HCI\_LE\_Long\_Term\_Key\_    Request\_Reply | 0x001A | Connection\_Handle    Long\_Term\_Key | status    Connection\_Handle |

5）LL B收到LTK之后，会向LL A回应一个LL\_ENC\_ RSP PDU，该PDU的格式为：

> |  |  |
> | --- | --- |
> | SKDs (8 octets) | IVs (4 octets) |
>
> SKDs和LL A的SDKm共同组成128bits的SKD；   
> IVs和LL A的IVm共同组成64bits的IV。

6）LL A收到LL\_ENC\_ RSP PDU之后，可以向LL B发送LL\_START\_ENC\_REQ PDU，开启Encryption，LL B则回应LL\_START\_ENC\_RSP PDU，这两个PDU均不携带任何的参数。

加密start之后，双方就可以安全的通信了。当然，LE encryption还提供了其它诸如暂停加密（LL\_PAUSE\_ENC\_REQ/LL\_PAUSE\_ENC\_RSP）、重启加密等过程，比较简单，这里就不详细介绍了，具体可参考BLE Spec[2]中的相关描述。

## 5. 参考文档

[1] [蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)

[2] Core\_v4.2.pdf

[3] [蓝牙协议分析(9)\_BLE安全机制之LL Privacy](/bluetooth/ble_ll_privacy.html)

[4] [蓝牙协议分析(8)\_BLE安全机制之白名单](/bluetooth/ble_white_list.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/le_encryption.html)。
