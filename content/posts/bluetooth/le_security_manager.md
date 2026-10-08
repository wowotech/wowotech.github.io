---
title: "蓝牙协议分析(11)_BLE安全机制之SM"
date: 2017-09-07T19:49:57+08:00
url: "/bluetooth/le_security_manager.html"
gid: "409"
emlog_type: "blog"
summary: "\r\n\t注1：此SM是Security Manager的缩写，非彼SM，大家不要理解歪了！ \r\n\r\n\r\n\t书接上文，我们在“蓝牙协议分析(10)_BLE安全机制之LE Encryption”中介绍了BLE安全机制中的终极武器----数据加密。不过使用这把武器有个前提，那就是双方要共同拥有一个加密key（LTK，Long Term Key）。这个key至关重要，怎么生成、怎么由通信的双方共享，关系到加"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "BLE", "SMP", "配对", "pairing", "鉴权", "authentication", "security"]
views: 95323
comment_count: 19
aliases:
  - "/bluetooth/409.html"
  - "/409.html"
---

## 1. 前言

注1：此SM是Security Manager的缩写，非彼SM，大家不要理解歪了！

书接上文，我们在“[蓝牙协议分析(10)\_BLE安全机制之LE Encryption](/bluetooth/le_encryption.html)”中介绍了BLE安全机制中的终极武器----数据加密。不过使用这把武器有个前提，那就是双方要共同拥有一个加密key（LTK，Long Term Key）。这个key至关重要，怎么生成、怎么由通信的双方共享，关系到加密的成败。因此蓝牙协议定义了一系列的复杂机制，用于处理和加密key有关的操作，这就是SM（Security Manager）。

另外，在加密链路建立之后，通信的双方可以在该链路上共享其它的key（例如在“[蓝牙协议分析(9)\_BLE安全机制之LL Privacy](/bluetooth/ble_ll_privacy.html)”中提到的IRK），SM也顺便定义了相应的规范。

## 2. Security Manager介绍

SM在蓝牙协议中的位置如下图：

[![SM_in_BLE_protocol](/content/uploadfile/201709/48d8dc6686ffabc4f8fd9b05ec11742020170907114954.gif "SM_in_BLE_protocol")](/content/uploadfile/201709/dfea88b9a77eb13a7187c785ca51566920170907114954.gif)

图片1 SM\_in\_BLE\_protocol

它的主要目的是为LE设备（LE only或者BR/EDR/LE）提供建立加密连接所需的key（STK or LTK）。为了达到这个目的，它定义了如下几类规范：

> 1）将生成加密key的过程称为Pairing（配对），并详细定义了Pairing的概念、操作步骤、实现细节等。
>
> 2）定义一个密码工具箱（Cryptographic Toolbox），其中包含了配对、加密等过程中所需的各种加密算法。
>
> 3）定义一个协议（Security Manager Protocol，简称SMP），基于L2CAP连接，实现master和slave之间的配对、密码传输等操作。

## 3. Pairing（配对）

在SM的规范中，配对是指“Master和Slave通过协商确立用于加（解）密的key的过程”，主要由三个阶段组成：

[![BLE_Pairing_Phases](/content/uploadfile/201709/c7f44b291f09092fe43cb6d4f291efe520170907114955.gif "BLE_Pairing_Phases")](/content/uploadfile/201709/7c14f6017a58c1091d818827d0100b2620170907114955.gif)

图片2 LE Pairing Phases

阶段1，称作“Pairing Feature Exchange”，用于交换双方有关鉴权的需求（authentication requirements），以及双方具有怎么的人机交互能力（IO capabilities）。

阶段2，通过SMP协议进行实际的配对操作，根据阶段1 “Feature Exchange”的结果，有两种配对方法可选：LE legacy pairing和LE Secure Connections。

阶段3是可选的，经过阶段1和阶段2之后，双方已经产生了加密key，因而可以建立加密的连接。加密连接建立后，可以互相传送一些私密的信息，例如Encryption Information、Identity Information、Identity Address Information等。

#### 3.1 Pairing Feature Exchange

配对的过程总是以Pairing Request和Pairing Response的协议交互开始，通过这两个命令，配对的发起者（Initiator，总是Master）和配对的回应者（Responder，总是Slave）可以交换足够的信息，以决定在阶段2使用哪种配对方法、哪种鉴权方式、等等，具体包括：

**3.1.1 配对方法**

Master和Slave有两种可选的配对方法：LE legacy pairing和LE Secure Connections（具体可参考后面3.2和3.3章节的介绍）。从命名上看，前者是过去的方法，后者是新方法。选择的依据是：

> 当Master和Slave都支持LE Secure Connections（新方法）的时候，则使用LE Secure Connections。否则，使用LE legacy pairing。

**3.1.2 鉴权方式**

所谓的鉴权（Authentication），就是要保证执行某一操作的双方（或者多方，这里就是配对的双方）的身份的合法性，不能出现“上错花轿嫁对郎”的情况。那怎么保证呢？从本质上来说就是通过一些额外的信息，告诉对方：现在正在和你配对的是“我”，是那个你正要配对的“我”！说起来挺饶舌，没关系，看看下面的实现方法就清楚了。

对BLE来说，主要有三类鉴权的方法（其实是两种），如下：

1）由配对的双方，在配对过程之外，额外的交互一些信息，并以这些信息为输入，进行后续的配对操作。这些额外信息也称作OOB（out of band），OOB的交互过程称为OOB protocol（是一个稍微繁琐的过程，这里不在详细介绍了）。

2）让“人（human）”参与进来，例如：

> 手机A向手机B发起配对操作的时候，手机A在界面上显示一串6位数字的配对码，并将该配对码发送给手机B，手机B在界面上显示同样的配对码，并要求用户确认A和B显示的配对码是否相同，如果相同，在B设备上点击配对即可配对成功（如下如所示）。
>
> [![配对码](/content/uploadfile/201709/08e64e522332c09c82504d45fbeb7f2020170907114956.gif "配对码")](/content/uploadfile/201709/e79b28a3fa0f266f0c175e8b483f973e20170907114956.gif)
>
> 图片3 配对码

这种需要人参与的鉴权方式，在蓝牙协议里面称作MITM（man-in-the-middle）authentication，不过由于BLE设备的形态千差万别，硬件配置也各不相同，有些可以输入可以显示、有些只可输入不可显示、有些只可显示不可输入、有些即可输入也可显示，因此无法使用统一的方式进行MITM鉴权（例如没有显示的设备无法使用上面例子的方式进行鉴权）。为此Security Manager定义了多种交互方法：

2a）Passkey Entry，通过输入配对码的方式鉴权，有两种操作方法

> 用户在两个设备上输入相同的6个数字（要求两个设备都有数字输入的能力），接下来的配对过程会进行相应的校验；
>
> 一个设备（A）随机生成并显示6个数字（要求该设备有显示能力），用户记下这个数字，并在另一个设备（B）上输入。设备B在输入的同时，会通过SMP协议将输入的数字同步的传输给设备A，设备A会校验数字是否正确，以达到鉴权的目的。

2b）Numeric Comparison，两个设备自行协商生成6个数字，并显示出来（要求两个设备具有显示能力），用户比较后进行确认（一致，或者不一致，要求设备有简单的yes or no的确认能力）。

2c）Just Work，不需要用户参与，两个设备自行协商。

3）不需要鉴权，和2c中的Just work的性质一样。

**3.1.3 IO Capabilities**

由3.1.2的介绍可知，Security Manager抽象出来了三种MITM类型的鉴权方法，这三种方法是根据两个设备的IO能力，在“Pairing Feature Exchange”阶段自动选择的。IO的能力可以归纳为如下的六种：

> NoInputNoOutput   
> DisplayOnly   
> NoInputNoOutput1   
> DisplayYesNo   
> KeyboardOnly   
> KeyboardDisplay

具体可参考BT SPEC[3] “BLUETOOTH SPECIFICATION Version 4.2 [Vol 3, Part H]” “2.3.2 IO Capabilities”中的介绍。

**3.1.4 鉴权方法的选择**

在“Pairing Feature Exchange”阶段，配对的双方以下面的原则选择鉴权方法：

> 1）如果双方都支持OOB鉴权，则选择该方式（优先级最高）。
>
> 2）否则，如果双方都支持MITM鉴权，则根据双方的IO Capabilities（并结合具体的配对方法），选择合适的鉴权方式（具体可参考BT SPEC[3] “BLUETOOTH SPECIFICATION Version 4.2 [Vol 3, Part H]”“2.3.5.1 Selecting Key Generation Method”中的介绍）。
>
> 3）否则，使用Just work的方式（不再鉴权）。

#### 3.2 LE legacy pairing

LE legacy pairing的过程比较简单，总结如下（可以参考下面的流程以辅助理解）：

[![LE_legacy_pairing](/content/uploadfile/201709/064a02c5fe5bc8112f3debba73d9dc0020170907114957.gif "LE_legacy_pairing")](/content/uploadfile/201709/2816906c8f3e088a06ec62f8a8bbfd2920170907114956.gif)

图片4 LE legacy pairing过程

1）LE legacy pairing最终生成的是Short Term Key（双方共享），生成STK之后，参考[1]中的介绍，用STK充当LTK，并将EDIV和Rand设置为0，去建立加密连接。

2）加密连接建立之后，双方可以自行生成Long Term Key（以及相应的EDIV和Rand），并通过后续的“Transport Specific Key Distribution”将它们共享给对方，以便后面重新建立加密连接所使用：

> master和slave都要生成各自的LTK/EDIV/Rand组合，并共享给对方。因为加密链路的发起者需要知道对方的LTK/EDIV/Rand组合，而Master或者Slave都有可能重新发起连接。
>
> 另外我们可以思考一个问题（在[1]中就应该有这个疑问）：为什么LE legacy pairing的LTK需要EDIV/Rand信息呢？因为LTK是各自生成的，不一样，因而需要一个索引去查找某一个LTK（对比后面介绍的LE Secure Connections，LTK是直接在配对是生成的，因而就不需要这两个东西）。

3）STK的生成也比较简单，双方各提供一个随机数（MRand和SRand），并以TK为密码，执行S1加密算法即可。

4）TK是实在鉴权的过程中得到的，根据在阶段一选择的鉴权方法，TK可以是通过OOB得到，也可以是通过Passkey Entry得到，也可以是0（Just Work）。

> LE legacy pairing只能使用OOB、Passkey Entry或者Just Work三种鉴权方法（Numeric Comparison只有在LE Secure Connections时才会使用）。

#### 3.3 LE Secure Connections Pairing

LE Secure Connections pairing利用了椭圆曲线加密算法（P-256 elliptic curve），简单说明如下（具体细节可参考看蓝牙SPEC[3]，就不在这里罗列了）：

1）可以使用OOB、Passkey Entry、Just Work以及Numeric Comparison四种鉴权方法。其中Numeric Comparison的流程和Just Work基本一样。

2）可以直接生成LTK（双方共享），然后直接使用LTK进行后续的链路加密，以及重新连接时的加密。

#### 3.4 Transport Specific Key Distribution

加密链路建立之后，通信的双方就可以传输一些比较私密的信息，主要包括：

> Encryption Information (Long Term Key)   
> Master Identification (EDIV, Rand)   
> Identity Information (Identity Resolving Key)   
> Identity Address Information (AddrType, BD\_ADDR)   
> Signing Information (Signature Key)

至于这些私密信息要怎么使用，就不在本文的讨论范围了，后续碰到的时候再介绍。

## 4. Security Manager Protocol介绍

SMP使用固定的L2CAP channel（CID为0x0006）传输Security相关的命令。它主要从如下的方面定义SM的行为（比较简单，不再详细介绍）：

1）规定L2CAP channel的特性，MTU、QoS等。

2）规定SM命令格式。

3）定义配对相关的命令，包括：

> Pairing Request   
> Pairing Response   
> Pairing Confirm   
> Pairing Random   
> Pairing Failed   
> Pairing Public Key   
> Pairing DHKey Check   
> Keypress Notification

4）定义鉴权、配对、密码交互等各个过程。

## 5. 密码工具箱介绍

为了执行鉴权、配对等过程，SM定义了一组密码工具箱，提供了十八般加密算法，由于太专业，就不在这里介绍了，感兴趣的读者直接去看spec就行了（“BLUETOOTH SPECIFICATION Version 4.2 [Vol 3, Part H] 2.2 CRYPTOGRAPHIC TOOLBOX”）。

## 6. Security Manager的使用

相信经过本文的介绍，大家对BLE的SM有了一定的了解，不过应该会有一个疑问：

> 这么复杂的过程，从应用角度该怎么使用呢？

放心，蓝牙协议不会给我们提供这么简陋的接口的，参考上面图片1，SM之上不是还有GAP吗？对了，真正使用SM功能之前，需要再经过GAP进行一次封装，具体可参考本站后续的文章。

## 7. 参考文档

[1] [蓝牙协议分析(10)\_BLE安全机制之LE Encryption](/bluetooth/le_encryption.html)

[2] [蓝牙协议分析(9)\_BLE安全机制之LL Privacy](/bluetooth/ble_ll_privacy.html)

[3] Core\_v4.2.pdf

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/le_security_manager.html)。
