---
title: "Linux I2C framework(2)_I2C provider"
date: 2016-02-26T22:49:20+08:00
url: "/comm/i2c_provider.html"
gid: "267"
emlog_type: "blog"
summary: "本文从Provider的角度，介绍怎么借助I2C framework管理I2C相关的SOC资源。换句话说，就是怎么编写I2C controller驱动。"
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "driver", "I2C"]
views: 24779
comment_count: 13
aliases:
  - "/comm/267.html"
  - "/267.html"
---

#### 1. 前言

本文从Provider的角度，介绍怎么借助I2C framework管理I2C相关的SOC资源。换句话说，就是怎么编写I2C controller驱动。

#### 2. 关键数据结构和API介绍

##### 2.1 I2C adapter

由“[Linux I2C framework(1)\_概述](/comm/i2c_overview.html)”可知，I2C framework使用struct i2c\_adapter抽象I2C控制器，具体如下：

```
  1: /* include/linux/i2c.h */
  2: 
  3: /*
  4:  * i2c_adapter is the structure used to identify a physical i2c bus along
  5:  * with the access algorithms necessary to access it.
  6:  */
  7: struct i2c_adapter {
  8:         struct module *owner;
  9:         unsigned int class;               /* classes to allow probing for */
 10:         const struct i2c_algorithm *algo; /* the algorithm to access the bus */
 11:         void *algo_data;
 12: 
 13:         /* data fields that are valid for all devices   */
 14:         struct rt_mutex bus_lock;
 15: 
 16:         int timeout;                    /* in jiffies */
 17:         int retries;
 18:         struct device dev;              /* the adapter device */
 19: 
 20:         int nr;
 21:         char name[48];
 22:         struct completion dev_released;
 23: 
 24:         struct mutex userspace_clients_lock;
 25:         struct list_head userspace_clients;
 26: 
 27:         struct i2c_bus_recovery_info *bus_recovery_info;
 28: };
```

> 该数据结构比较简单，只需要着重关注如下事项：
>
> 1）由它的注释可知，struct i2c\_adapter是用于标识物理的I2C总线（physical i2c bus），且该总线需要有一套用于访问slave设备的算法（access algorithm）。
>
> 2）所谓的access algorithm，就是通过I2C总线发送和接收数据的方法，它保存在algo指针（struct i2c\_algorithm，具体可参考后续2.2小节的描述）中。
>
> 3）基于I2C传输的特性，不一定每一次总线访问（发送或者接收数据）都会成功，在传输失败的时候，可以选择重试。重试的逻辑由I2C core自行完成，但I2C controller driver需要设定重试的次数，这就是retries字段的意义。另外，有些consumer对结果的返回是有时间要求的，因此不能无节制的重试，timeout字段（单位为jiffies）在retries基础上，增加了时间限制，超过这个时间，就不能重试了。
>
> 4）nr，该I2C bus的ID，会体现在sysfs中（/sys/bus/i2c/devices/i2c-n中的‘n’），可由I2C controller driver在注册adapter时指定，或者通过DTS解析（后面会介绍），或者自动分配。
>
> 5）class，该I2C bus支持哪些类型的slave device，只有匹配的slave device才能和bus绑定。具体的类型包括（可参考include/linux/i2c.h中的定义和注释）：
>   
>  I2C\_CLASS\_HWMON，硬件监控类，如lm\_sensors等；
>   
>  I2C\_CLASS\_DDC，DDC是数字显示通道（Digital Display Channel）的意思， 通常用于显示设备信息的获取；
>   
>  I2C\_CLASS\_SPD，存储类的模组；
>   
>  I2C\_CLASS\_DEPRECATED，不再使用的class。
>
> 6）dev，我们在“[Linux I2C framework(1)\_概述](/comm/i2c_overview.html)”的第2章提到过，I2C framework将I2C adapter当做了I2C bus中的一类特殊的设备，因此dev变量是它在设备模型中的体现。

##### 2.2 i2c algorithm

由2.1的描述可知，struct i2c\_algorithm抽象了通过I2C总线发送和接收数据的方法，其定义如下：

```
  1: /* include/linux/i2c.h */
  2: 
  3: /**
  4:  * struct i2c_algorithm - represent I2C transfer method
  5:  * @master_xfer: Issue a set of i2c transactions to the given I2C adapter
  6:  *   defined by the msgs array, with num messages available to transfer via
  7:  *   the adapter specified by adap.
  8:  * @smbus_xfer: Issue smbus transactions to the given I2C adapter. If this
  9:  *   is not present, then the bus layer will try and convert the SMBus calls
 10:  *   into I2C transfers instead.
 11:  * @functionality: Return the flags that this algorithm/adapter pair supports
 12:  *   from the I2C_FUNC_* flags.
 13:  *
 14:  * The following structs are for those who like to implement new bus drivers:
 15:  * i2c_algorithm is the interface to a class of hardware solutions which can
 16:  * be addressed using the same bus algorithms - i.e. bit-banging or the PCF85
 17:  * to name two of the most common.
 18:  *
 19:  * The return codes from the @master_xfer field should indicate the type of
 20:  * error code that occured during the transfer, as documented in the kernel
 21:  * Documentation file Documentation/i2c/fault-codes.
 22:  */
 23: struct i2c_algorithm {
 24:         /* If an adapter algorithm can't do I2C-level access, set master_xfer
 25:            to NULL. If an adapter algorithm can do SMBus access, set
 26:            smbus_xfer. If set to NULL, the SMBus protocol is simulated
 27:            using common I2C messages */
 28:         /* master_xfer should return the number of messages successfully
 29:            processed, or a negative value on error */
 30:         int (*master_xfer)(struct i2c_adapter *adap, struct i2c_msg *msgs,
 31:                            int num);
 32:         int (*smbus_xfer) (struct i2c_adapter *adap, u16 addr,
 33:                            unsigned short flags, char read_write,
 34:                            u8 command, int size, union i2c_smbus_data *data);
 35: 
 36:         /* To determine what the adapter supports */
 37:         u32 (*functionality) (struct i2c_adapter *);
 38: };
```

1）functionality，通过一个bitmap，告诉调用者该I2C adapter支持的功能，包括（具体可参考include/uapi/linux/i2c.h中的定义和注释）：

> I2C\_FUNC\_I2C，支持传统的I2C功能；
>   
> I2C\_FUNC\_10BIT\_ADDR，支持10bit地址；
>   
> I2C\_FUNC\_PROTOCOL\_MANGLING，支持非标准的协议行为（具体请参考2.3小节的介绍）；
>   
> I2C\_FUNC\_NOSTART，支持不需要发送START信号的I2C传输（具体请参考2.3小节的介绍）；
>   
> I2C\_FUNC\_SMBUS\_xxx，SMBUS相关的功能，不再详细介绍。

2）master\_xfer，I2C协议有关的数据传输接口，输入参数是struct i2c\_msg类型（可参考2.3小节的介绍）的数组（大小由num指定）。返回值是成功传输的msg的个数，如有错误返回负值。

3）smbus\_xfer，SMBUS有关的数据传输接口，如果为NULL，I2C core会尝试使用master\_xfer模拟。

##### 2.3 i2c msg

由2.2的介绍可知，I2C传输（读或者写）以i2c msg为单位，该数据结构的定义如下：

```
  1: /* include/uapi/linux/i2c.h */
  2: 
  3: struct i2c_msg {
  4:         __u16 addr;     /* slave address                        */
  5:         __u16 flags;
  6: #define I2C_M_TEN               0x0010  /* this is a ten bit chip address */
  7: #define I2C_M_RD                0x0001  /* read data, from slave to master */
  8: #define I2C_M_STOP              0x8000  /* if I2C_FUNC_PROTOCOL_MANGLING */
  9: #define I2C_M_NOSTART           0x4000  /* if I2C_FUNC_NOSTART */
 10: #define I2C_M_REV_DIR_ADDR      0x2000  /* if I2C_FUNC_PROTOCOL_MANGLING */
 11: #define I2C_M_IGNORE_NAK        0x1000  /* if I2C_FUNC_PROTOCOL_MANGLING */
 12: #define I2C_M_NO_RD_ACK         0x0800  /* if I2C_FUNC_PROTOCOL_MANGLING */
 13: #define I2C_M_RECV_LEN          0x0400  /* length will be first received byte */
 14:         __u16 len;              /* msg length                           */
 15:         __u8 *buf;              /* pointer to msg data                  */
 16: };
```

> 1）addr，I2C slave device的地址。
>
> 2）flags，数据传输可携带的flag，包括（具体可参考include/uapi/linux/i2c.h中的定义和注释）：
>   
>  I2C\_M\_TEN，支持10-bit的slave地址；
>   
>  I2C\_M\_RD，此次传输是读操作；
>   
>  其它flag，下面再详细描述。
>
> 3）len，数据传输的长度，单位为byte。
>
> 4）buf，数据buf。

##### 2.4 I2C传输有关的flags

正常情况下，如果I2C msg中的flags为0，adapter将按照标准I2C协议操作总线，进行传输操作，即（具体可参考Documentation/i2c/i2c-protocol）：

> 写操作：
>
> S Addr Wr [A] Data [A] Data [A] ... [A] Data [A] P
>
> 读操作：
>
> S Addr Rd [A] [Data] A [Data] A ... A [Data] NA P
>
> 注1：对读操作来说，当master收到slave发送的NA（NACK）消息时，表明已经没有数据可读，应当停止读取（当然，有例外，下面会介绍）。
>
> 读写混合操作：
>
> S Addr Rd [A] [Data] NA S Addr Wr [A] Data [A] P

否则，可按照flags中指定的行为，进行非标的I2C传输（当然，adapter需要支持，具体可参考2.2小节中有关functionality的介绍），这些flag包括：

1）I2C\_M\_IGNORE\_NAK

读操作的时候，忽略slave返回的NA，把它当做ACK信号，继续读取。还别说，那真有那比较贱的slave，比如电视（通过I2C读取EDID的时候）。

2）I2C\_M\_NO\_RD\_ACK

读操作的时候，忽略所有的NACK/ACK信号。（霸气，不过没用过！）

3）I2C\_M\_NOSTART

读写混合操作的情况下，假如要传输多个msg（以2个为例），如果第二个msg携带了该标志，则不再发送'S Addr Wr/Rd [A]'信号，即从

> S Addr Rd [A] [Data] NA S Addr Wr [A] Data [A] P
>
> S Addr Rd [A] [Data] NA S Addr Wr [A] Data [A] P

变为

> S Addr Rd [A] [Data] NA S Addr Wr [A] Data [A] P
>
> S Addr Rd [A] [Data] NA Data [A] P

奇奇怪怪的场景啊，用到的时候再仔细阅读kernel的document吧。

4）I2C\_M\_REV\_DIR\_ADDR，将读写flag翻转，即读的时候发Wr信号，写的时候发Rd信号。至于为什么这么用，只有天知道。

5）I2C\_M\_STOP，msg传输完成后forece STOP。不太明白现实意义，用过的同学帮忙科普一下。

6）I2C\_M\_RECV\_LEN，SMBUS的一个flag，意义不明。

##### 2.5 I2C adapter相关的API

I2C adapter定义好之后，要把它注册到kernel中去，相关的API如下：

```
  1: /* include/linux/i2c.h */
  2: 
  3: extern int i2c_add_adapter(struct i2c_adapter *);
  4: extern void i2c_del_adapter(struct i2c_adapter *);
  5: extern int i2c_add_numbered_adapter(struct i2c_adapter *);
  6: 
  7: static inline u32 i2c_get_functionality(struct i2c_adapter *adap)
  8: static inline int i2c_check_functionality(struct i2c_adapter *adap, u32 func)
  9: static inline int i2c_adapter_id(struct i2c_adapter *adap)
 10: 
 11: extern struct i2c_adapter *i2c_get_adapter(int nr);
 12: extern void i2c_put_adapter(struct i2c_adapter *adap);
 13: 
 14: /* must call put_device() when done with returned i2c_adapter device */
 15: extern struct i2c_adapter *of_find_i2c_adapter_by_node(struct device_node *node);
```

> 1）i2c\_add\_adapter和i2c\_add\_numbered\_adapter是I2C adapter的注册接口，它们的区别是：i2c\_add\_adapter会自动分配adapter ID（adapter->nr，见2.1），i2c\_add\_numbered\_adapter则可以指定ID（adapter->nr需要时有效值，否则会调用i2c\_add\_adapter自动分配）。
>
> 2）i2c\_del\_adapter将I2C adapter从内核中删除。
>
> 3）i2c\_get\_functionality获取指定adapter所支持的功能，i2c\_check\_functionality可用于检查指定adapter是否具备指定功能。
>
> 4）i2c\_adapter\_id可以获取指定adapter的ID。
>
> 5）i2c\_get\_adapter通过ID获得指定adapter的指针，由于该接口会尝试调用try\_module\_get增加模块的引用计数，因此使用完毕后，需要调用i2c\_put\_adapter将引用计数减去。
>
> 6）of\_find\_i2c\_adapter\_by\_node，通过device的device\_node查找相应的adapter结构，使用完后需要调用put\_device将adapter->dev所在的模块引用计数减去。

#### 3. 编写I2C controller驱动的步骤

了解了I2C adapter有关的数据结构和API之后，编写I2C控制器驱动就简单多了，主要步骤如下：

1）定义一个struct i2c\_algorithm变量，并根据I2C controller的特性，实现其中的回调函数。

2）在DTS文件（一般都放到DTSI）中，定义I2C controller相关的DTS node，例如：

```
  1: /* arch/arm/boot/dts/am33xx.dtsi
  2: 
  3: i2c0: i2c@44e0b000 {
  4:         compatible = "ti,omap4-i2c";
  5:         #address-cells = <1>;
  6:         #size-cells = <0>;
  7:         ti,hwmods = "i2c1";
  8:         reg = <0x44e0b000 0x1000>;
  9:         interrupts = <70>;
 10:         status = "disabled";
 11: };
 12: 
 13: i2c1: i2c@4802a000 {
 14:         compatible = "ti,omap4-i2c";
 15:         #address-cells = <1>;
 16:         #size-cells = <0>;
 17:         ti,hwmods = "i2c2";
 18:         reg = <0x4802a000 0x1000>;
 19:         interrupts = <71>;
 20:         status = "disabled";
 21: };
 22: 
 23: ...
```

3）在drives/i2c/busses目录下，以i2c-xxx.c的命名方式，编写I2C controller的platform driver,并提供match id、probe、remove等接口。

4）在platform driver的probe接口中，分配一个adapter结构，并进行必要的初始化操作后，调用i2c\_add\_adapter或者i2c\_add\_numbered\_adapter接口，将其注册到kernel中即可。

#### 4. i2c\_add\_adapter流程分析

最后，我们简单的看一下i2c adapter的add流程，主要关注三点：adapter ID的分配；设备模型有关的内容；I2C slave device的创建和注册。

##### 4.1 adapter ID的分配

由第2章的描述可知，I2C adapter ID（adapter->nr）可通过两种方法分配，一种是driver直接赋值，并经过下面的函数调用注册adapter（具体可参考drivers/i2c/i2c-core.c）：

> i2c\_add\_numbered\_adapter--->\_\_i2c\_add\_numbered\_adapter--->i2c\_register\_adapter

另一种方法，是调用i2c\_add\_adapter动态分配，如下：

```
  1: /* drivers/i2c/i2c-core.c */
  2: 
  3: int i2c_add_adapter(struct i2c_adapter *adapter)
  4: {
  5:         struct device *dev = &adapter->dev;
  6:         int id;
  7: 
  8:         if (dev->of_node) {
  9:                 id = of_alias_get_id(dev->of_node, "i2c");
 10:                 if (id >= 0) {
 11:                         adapter->nr = id;
 12:                         return __i2c_add_numbered_adapter(adapter);
 13:                 }
 14:         }
 15: 
 16:         mutex_lock(&core_lock);
 17:         id = idr_alloc(&i2c_adapter_idr, adapter,
 18:                        __i2c_first_dynamic_bus_num, 0, GFP_KERNEL);
 19:         mutex_unlock(&core_lock);
 20:         if (id < 0)
 21:                 return id;
 22: 
 23:         adapter->nr = id;
 24: 
 25:         return i2c_register_adapter(adapter);
 26: }
```

动态分配也有两种手段：

8~13行，通过of\_alias\_get\_id获取。该方法会通过DTS中的alias解析指定I2C adapter的ID，例如：

> aliases {
>   
>  i2c0 = &i2c0;
>   
> };
>
> i2c0: i2c@44e0b000 {
>   
>  compatible = "ti,omap4-i2c";
>   
>  …
>   
> };
>
> /\* arch/arm/boot/dts/am33xx.dtsi \*/
>
> 相关讨论可参考“[/device_model/dt_basic_concept.html](/device_model/dt_basic_concept.html "/device_model/dt_basic_concept.html")”留言中的讨论。

16~19，通过idr\_alloc分配（idr也是比较好玩的一个功能，有空分析一下，这里不再细述了）。

最后，在较新版本的kernel中，adapter ID的作用仅仅体现在sysfs中，即：

> /sys/bus/i2c/devices/i2c-n/
>   
> ---->/sys/devices/xxxxxxxx.i2c/i2c-n
>
> 中的‘n’。

##### 4.2 设备模型有关的流程

adapter ID分配完后，或执行i2c\_register\_adapter，该接口会在“/sys/devices/xxxxxxxx.i2c/”中创建该adapter的目录（/sys/devices/xxxxxxxx.i2c/i2c-n），如下：

> dev\_set\_name(&adap->dev, "i2c-%d", adap->nr);
>   
> adap->dev.bus = &i2c\_bus\_type;
>   
> adap->dev.type = &i2c\_adapter\_type;
>   
> res = device\_register(&adap->dev);

由此可知，I2C adapter被挂到i2c总线（i2c\_bus\_type）上了，同时，通过“device\_register--->device\_add--->bus\_add\_device--->sysfs\_create\_link”的调用，在/sys/bus/i2c/devices/中创建对应的符号链接（/sys/bus/i2c/devices/i2c-n/）。支持，I2C adapter有关的设备模型结构，在sysfs中创建完毕。

注2：adapter的目录创建的位置，取决于adapter->dev的parent的设备，通常是I2C控制器所对应的platform设备，如：

> static int
>   
> omap\_i2c\_probe(struct platform\_device \*pdev)
>   
> {
>   
>  …
>   
>  adap->dev.parent = &pdev->dev;
>   
>  …
>   
> }

##### 4.3 I2C slave device的创建和注册

在DTS的支持下，I2C adapter注册的时候，会为它下面所有的slave device创建struct i2c\_client结构，并注册到I2C bus上，调用流程是：

> i2c\_register\_adapter--->of\_i2c\_register\_devices--->i2c\_new\_device

由于牵涉到I2C consumer的DTS结构，该部分内容下一篇文章再介绍。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/i2c_provider.html)。
