---
title: "蓝牙协议分析(6)_BLE地址类型"
date: 2016-06-07T11:40:03+08:00
url: "/bluetooth/ble_address_type.html"
gid: "305"
emlog_type: "blog"
summary: "也许关注BLE的同学都注意到了，BLE设备有多种类型的设备地址，如Public Device Address、Random Device Address、Static Device Address、Private Device Address等等。如果不了解内情，大家肯定会被它们绕晕。不过存在即合理，这样看似奇怪的设计，实际上反映了BLE的设计思路以及所针对的应用场景。让我们通过本文一窥究竟。"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "BLE", "public", "random", "static", "private", "resolvable", "address"]
views: 83140
comment_count: 46
aliases:
  - "/bluetooth/305.html"
  - "/305.html"
---

#### 1. 前言

也许关注BLE的同学都注意到了，BLE设备有多种类型的设备地址，如Public Device Address、Random Device Address、Static Device Address、Private Device Address等等。如果不了解内情，大家肯定会被它们绕晕。不过存在即合理，这样看似奇怪的设计，实际上反映了BLE的设计思路以及所针对的应用场景。让我们通过本文一窥究竟。

#### 2. BLE设备的地址类型

一个BLE设备，可以使用两种类型的地址（一个BLE设备可同时具备两种地址）：Public Device Address和Random Device Address。而Random Device Address又分为Static Device Address和Private Device Address两类。其中Private Device Address又可以分为Non-resolvable Private Address和Resolvable Private Address。它们的关系如下所示：

```
                        Public Device 

                  +--->    Address 

+-------------+   | 

|             |   | 

|     BLE     |   | 

|    Device   +---+       or/and           Static Device 

|             |   |                    +-->   Address 

+-------------+   |                    | 

                  |     Random Device  | 

                  +---->   Address   +-+       or               Non-resolvable 

                                       |                    +-> private address 

                                       |                    | 

                                       |   Private Device   |       or 

                                       +-->    Address   +--+ 

                                                            |      Resolvable 

                                                            +-> private address 
```

#### 3. Public Device Address

在通信系统中，设备地址是用来唯一识别一个物理设备的，如TCP/IP网络中的MAC地址、传统蓝牙中的蓝牙地址等。对设备地址而言，一个重要的特性，就是唯一性（或者说一定范围内的唯一），否则很有可能造成很多问题。蓝牙通信系统也不例外。

对经典蓝牙（BR/EDR）来说，其设备地址是一个48bits的数字，称作"48-bit universal LAN MAC addresses(和电脑的MAC地址一样)“。正常情况下，该地址需要向IEEE申请（其实是购买[1]，呵呵！）。企业交钱，IEEE保证地址的唯一性，皆大欢喜。

当然，这种地址分配方式，在BLE中也保留下来了，就是Public Device Address。Public Device Address由24-bit的company\_id和24-bit的company\_assigned组成，具体可参考蓝牙Spec中相关的说明[2]。

#### 4. Random Device Address

但是，在BLE时代，只有Public Device Address还不够，有如下原因：

> 1）Public Device Address需要向IEEE购买。虽然不贵，但在BLE时代，相比BLE IC的成本，还是不小的一笔开销。
>
> 2）Public Device Address的申请与管理是相当繁琐、复杂的一件事情，再加上BLE设备的数量众多（和传统蓝牙设备不是一个数量级的），导致维护成本增大。
>
> 3）安全因素。BLE很大一部分的应用场景是广播通信，这意味着只要知道设备的地址，就可以获取所有的信息，这是不安全的。因此固定的设备地址，加大了信息泄漏的风险。

为了解决上述问题，BLE协议新增了一种地址：Random Device Address，即设备地址不是固定分配的，而是在设备设备启动后随机生成的。根据不同的目的，Random Device Address分为Static Device Address和Private Device Address两类。

##### 4.1 Static Device Address

Static Device Address是设备在上电时随机生成的地址，格式如下：

```
LSB                                        MSB 

+------------------------------------+---+---+ 

|    Random part of static address   | 1 | 1 | 

+------------------------------------+---+---+ 

                static address 

<--------------+  (48 bits)  +---------------> 
```

  

Static Device Address的特征可总结为：

> 1）最高两个bit为“11”。
>
> 2）剩余的46bits是一个随机数，不能全部为0，也不能全部为1。
>
> 3）在一个上电周期内保持不变。
>
> 4）下一次上电的时候可以改变。但不是强制的，因此也可以保持不变。如果改变，上次保存的连接等信息，将不再有效。

Static Device Address的使用场景可总结为：

> 1）46bits的随机数，可以很好地解决“设备地址唯一性”的问题，因为两个地址相同的概率很小。
>
> 2）地址随机生成，可以解决Public Device Address申请所带来的费用和维护问题。

##### 4.2 Private Device Address

Static Device Address通过地址随机生成的方式，解决了部分问题，Private Device Address则更进一步，通过定时更新和地址加密两种方法，提高蓝牙地址的可靠性和安全性。根据地址是否加密，Private Device Address又分为两类，Non-resolvable private address和Resolvable private address。下面我们分别描述。

**4.2.1 Non-resolvable private address**

Non-resolvable private address和Static Device Address类似，不同之处在于，Non-resolvable private address会定时更新。更新的周期称是由GAP规定的，称作T\_GAP(private\_addr\_int) ，建议值是15分钟。其格式如下：

```
LSB                                        MSB 

+----------------------------------------+---+ 

|Random part of nonresolvable address| 0 | 0 | 

+----------------------------------------+---+ 

             nonresolvable address 

<--------------+  (48 bits)  +---------------> 
```

  

特征可总结为：

> 1）最高两个bit为“00”。
>
> 2）剩余的46bits是一个随机数，不能全部为0，也不能全部为1。
>
> 3）以T\_GAP(private\_addr\_int)为周期，定时更新。

注1：Non-resolvable private address有点奇怪，其应用场景并不是很清晰。地址变来变去的，确实是迷惑了敌人，但自己人不也一样被迷惑了吗？因此，实际产品中，该地址类型并不常用。

**4.2.2 Resolvable private address**

Resolvable private address比较有用，它通过一个随机数和一个称作identity resolving key (IRK) 的密码生成，因此只能被拥有相同IRK的设备扫描到，可以防止被未知设备扫描和追踪。其格式如下：

```
LSB                                                     MSB 

+--------------------------+----------------------+---+---+ 

|                          | Random part of prand | 1 | 0 | 

+--------------------------+----------------------+---+---+ 



<--------+ hash +---------> <-----------+ prand +-------> 

         (24 bits)                     （24 bits） 
```

  

特征如下：

> 1）由两部分组成：   
> 高位24bits是随机数部分，其中最高两个bit为“10”，用于标识地址类型；   
> 低位24bits是随机数和IRK经过hash运算得到的hash值，运算的公式为hash = ah(IRK, prand)。
>
> 2）当对端BLE设备扫描到该类型的蓝牙地址后，会使用保存在本机的IRK，和该地址中的prand，进行同样的hash运算，并将运算结果和地址中的hash字段比较，相同的时候，才进行后续的操作。这个过程称作resolve（解析），这也是Non-resolvable private address/Resolvable private address命名的由来。
>
> 3）以T\_GAP(private\_addr\_int)为周期，定时更新。哪怕在广播、扫描、已连接等过程中，也可能改变。
>
> 4）Resolvable private address不能单独使用，因此需要使用该类型的地址的话，设备要同时具备Public Device Address或者Static Device Address中的一种。

#### 5. Resolvable private address应用场景及HCI命令介绍

BLE Resolvable private address的解析和过滤操作是在Link Layer实现的，因而为BLE的广播通信提供了一个相对安全的加密环境。Link Layer以Resolving List的形式，通过HCI向Host提供相关的控制API，以实现相应的功能，相关的HCI命令介绍如下：

> LE Set Random Address Command，设置一个新的Random地址，包括Resolvable private address类型的地址。
>
> LE Add Device to Resolving List Command，将指定的设备添加到本机的Resolving List中，需要指定的参数包括：需要添加设备的地址（包括地址类型）、需要添加设备的IRK、本设备的IRK。
>
> LE Remove Device From Resolving List Command，将指定设备从本机的Resolving List中删除。
>
> LE Clear Resolving List Command，清除本机的Resolving List。
>
> LE Read Resolving List Size Command，读取本机Resolving List的大小。
>
> LE Read Peer Resolvable Address Command，读取对端设备解析后的Resolvable private address。
>
> LE Read Local Resolvable Address Command，读取本机设备解析后的Resolvable private address。
>
> LE Set Address Resolution Enable Command，禁止/使能地址解析功能。

总结和说明：

> 1）Resolvable private address的生成，是Host以T\_GAP(private\_addr\_int)为周期，主动进行的，并通过“LE Set Random Address Command”告知Controller的Link Layer。因此，如果本地设备需要安全的环境，可以使用Resolvable private address作为广播和连接地址。
>
> 2）如果本地设备需要和某一个使用Resolvable private address的设备通信（扫描、连接等），则需要将该设备添加到Resolving List中，并使能地址解析功能。只有地址解析正确的时候，Link Layer才会继续后续的通信动作。
>
> 3）如果地址解析不正确，本地设备向对方发送的所有的数据包（扫描请求、连接请求等），都不能被正确接收（因为目的地址不正确）。但有一个例外，如果本地设备直接关闭地址解析功能，还是能收到对方的广播包，因此，Resolvable private address并不能保护广播包的数据。如果有敏感信息，放到scan response packet中应该是一个不错的选择。
>
> 4）上面分析是否正确？我也不是十分有把握，后续可以做个实验看看。

#### 6. 参考文档

[1] OUI购买链接，[http://cn.ieee.org/OUI\_introduction.html,,,,,,,,,,,,,,,,](http://cn.ieee.org/OUI_introduction.html,http://standards.ieee.org/develop/regauth/oui/index.html "http://cn.ieee.org/OUI_introduction.html")[http://standards.ieee.org/develop/regauth/oui/index.html](http://standards.ieee.org/develop/regauth/oui/index.html "http://standards.ieee.org/develop/regauth/oui/index.html")

[2] Core\_v4.2.pdf

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ble_address_type.html)。
