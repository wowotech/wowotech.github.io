---
title: "Linux common clock framework(1)_概述"
date: 2014-10-20T23:06:59+08:00
url: "/pm_subsystem/clk_overview.html"
gid: "97"
emlog_type: "blog"
summary: "\r\n\tcommon clock framework是用来管理系统clock资源的子系统，根据职能，可分为三个部分：\r\n\r\n\r\n\t1）向其它driver提供操作clocks的通用API。\r\n\r\n\r\n\t2）实现clock控制的通用逻辑，这部分和硬件无关。\r\n\r\n\r\n\t3）将和硬件相关的clock控制逻辑封装成操作函数集，交由底层的platform开发者实现，由通用逻辑调用。\r\n\r\n\r\n\t因此，蜗蜗会将"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "clock", "API"]
views: 71146
comment_count: 32
aliases:
  - "/pm_subsystem/97.html"
  - "/97.html"
---

#### 1. 前言

common clock framework是用来管理系统clock资源的子系统，根据职能，可分为三个部分：

1）向其它driver提供操作clocks的通用API。

2）实现clock控制的通用逻辑，这部分和硬件无关。

3）将和硬件相关的clock控制逻辑封装成操作函数集，交由底层的platform开发者实现，由通用逻辑调用。

因此，蜗蜗会将clock framework的分析文章分为3篇：

第一篇为概述和通用API的使用说明，面向的读者是使用clock的driver开发者，目的是掌握怎么使用clock framework（就是本文）；

第二篇为底层操作函数集的解析和使用说明，面向的读者是platform clock driver的开发者，目的是掌握怎么借助clock framework管理系统的时钟资源；

第三篇为clock framework的内部逻辑解析，面向的读者是linux kernel爱好者，目的是理解怎么实现clock framework。

注1：任何framework的职能分类都是如此，因此都可以按照这个模式分析。

#### 2. 概述

如今，可运行Linux的主流处理器平台，都有非常复杂的clock tree，我们随便拿一个处理器的spec，查看clock相关的章节，一定会有一个非常庞大和复杂的树状图，这个图由clock相关的器件，以及这些器件输出的clock组成。下图是一个示例：

[![clock](/content/uploadfile/201410/305f3177f0d598e8173d6123648ca14620141020150657.gif "clock")](/content/uploadfile/201410/8321e8ac90bb43c1f00543082b74fbd820141020150656.gif)

clock相关的器件包括：用于产生clock的Oscillator（有源振荡器，也称作谐振荡器）或者Crystal（无源振荡器，也称晶振）；用于倍频的PLL（锁相环，Phase Locked Loop）；用于分频的divider；用于多路选择的Mux；用于clock enable控制的与门；使用clock的硬件模块（可称作consumer）；等等。

common clock framework的管理对象，就是上图蓝色字体描述的clock（在软件中用struct clk抽象，以后就简称clk），主要内容包括（不需要所有clk都支持）：

1）enable/disable clk。

2）设置clk的频率。

3）选择clk的parent，例如hw3\_clk可以选择osc\_clk、pll2\_clk或者pll3\_clk作为输入源。

#### 3. common clock framework提供的通用API

管理clock的最终目的，是让device driver可以方便的使用，这些是通过include/linux/clk.h中的通用API实现的，如下：

1）struct clk结构

一个系统的clock tree是固定的，因此clock的数目和用途也是固定的。假设上面图片所描述的是一个系统，它的clock包括osc\_clk、pll1\_clk、pll2\_clk、pll3\_clk、hw1\_clk、hw2\_clk和hw3\_clk。我们完全可以通过名字，抽象这7个clock，进行开/关、rate调整等操作。但这样做有一个缺点：不能很好的处理clock之间的级联关系，如hw2\_clk和hw3\_clk都关闭后，pll2\_clk才能关闭。因此就引入struct clk结构，以链表的形式维护这种关系。

同样的道理，系统的struct clk，也是固定的，由clock driver在系统启动时初始化完毕，需要访问某个clock时，只要获取它对应的struct clk结构即可。怎么获取呢？可以通过名字索引啊！很长一段时间内，kernel及driver就是使用这种方式管理和使用clock的。

最后，设备（由struct device表示）对应的clock（由struct clk表示）也是固定的啊，可不可以找到设备就能找到clock？可以，不过需要借助device tree。

注2：对使用者（device driver）来说，struct clk只是访问clock的一个句柄，不用关心它内部的具体形态。

2）clock获取有关的API

device driver在操作设备的clock之前，需要先获取和该clock关联的struct clk指针，获取的接口如下：

```
   1: struct clk *clk_get(struct device *dev, const char *id);
```

```
   2: struct clk *devm_clk_get(struct device *dev, const char *id);
```

```
   3: void clk_put(struct clk *clk);
```

```
   4: void devm_clk_put(struct device *dev, struct clk *clk);
```

```
   5: struct clk *clk_get_sys(const char *dev_id, const char *con_id);
```

```
   6:  
```

```
   7: struct clk *of_clk_get(struct device_node *np, int index);
```

```
   8: struct clk *of_clk_get_by_name(struct device_node *np, const char *name);
```

```
   9: struct clk *of_clk_get_from_provider(struct of_phandle_args *clkspec);
```

> a）clk\_get，以device指针或者id字符串（可以看作name）为参数，查找clock。
>
> a1）dev和id的任意一个可以为空。如果id为空，则必须有device tree的支持才能获得device对应的clk；
>   
>  a2）根据具体的平台实现，id可以是一个简单的名称，也可以 是一个预先定义的、唯一的标识（一般在平台提供的头文件中定义，如mach/clk.h）；
>   
>  a3）不可以在中断上下文调用。
>
> b）devm\_clk\_get，和clk\_get一样，只是使用了[device resource management](/device_model/device_resource_management.html)，可以自动释放。
>
> c）clk\_put、devm\_clk\_put，get的反向操作，一般和对应的get API成对调用。
>
> d）clk\_get\_sys，类似clk\_get，不过使用device的name替代device结构。
>
> e）of\_clk\_get、of\_clk\_get\_by\_name、of\_clk\_get\_from\_provider，device tree相关的接口，直接从相应的DTS node中，以index、name等为索引，获取clk，后面会详细说明。

3）clock控制有关的API

```
   1: int clk_prepare(struct clk *clk)
```

```
   2: void clk_unprepare(struct clk *clk)
```

```
   3:  
```

```
   4: static inline int clk_enable(struct clk *clk)
```

```
   5: static inline void clk_disable(struct clk *clk)
```

```
   6:  
```

```
   7: static inline unsigned long clk_get_rate(struct clk *clk)
```

```
   8: static inline int clk_set_rate(struct clk *clk, unsigned long rate)
```

```
   9: static inline long clk_round_rate(struct clk *clk, unsigned long rate)
```

```
  10:  
```

```
  11: static inline int clk_set_parent(struct clk *clk, struct clk *parent)
```

```
  12: static inline struct clk *clk_get_parent(struct clk *clk)
```

```
  13:  
```

```
  14: static inline int clk_prepare_enable(struct clk *clk)
```

```
  15: static inline void clk_disable_unprepare(struct clk *clk)
```

> a）clk\_enable/clk\_disable，启动/停止clock。不会睡眠。
>
> b）clk\_prepare/clk\_unprepare，启动clock前的准备工作/停止clock后的善后工作。可能会睡眠。
>
> c）clk\_get\_rate/clk\_set\_rate/clk\_round\_rate，clock频率的获取和设置，其中clk\_set\_rate可能会不成功（例如没有对应的分频比），此时会返回错误。如果要确保设置成功，则需要先调用clk\_round\_rate接口，得到和需要设置的rate比较接近的那个值。
>
> d）获取/选择clock的parent clock。
>
> e）clk\_prepare\_enable，将clk\_prepare和clk\_enable组合起来，一起调用。clk\_disable\_unprepare,将clk\_disable和clk\_unprepare组合起来，一起调用。

注2：prepare/unprepare，enable/disable的说明。

这两套API的本质，是把clock的启动/停止分为atomic和non-atomic两个阶段，以方便实现和调用。因此上面所说的“不会睡眠/可能会睡眠”，有两个角度的含义：一是告诉底层的clock driver，请把可能引起睡眠的操作，放到prepare/unprepare中实现，一定不能放到enable/disable中；二是提醒上层使用clock的driver，调用prepare/unprepare接口时可能会睡眠哦，千万不能在atomic上下文（例如中断处理中）调用哦，而调用enable/disable接口则可放心。

另外，clock的开关为什么需要睡眠呢？这里举个例子，例如enable PLL clk，在启动PLL后，需要等待它稳定。而PLL的稳定时间是很长的，这段时间要把CPU交出（进程睡眠），不然就会浪费CPU。

最后，为什么会有合在一起的clk\_prepare\_enable/clk\_disable\_unprepare接口呢？如果调用者能确保是在non-atomic上下文中调用，就可以顺序调用prepare/enable、disable/unprepared，为了简单，framework就帮忙封装了这两个接口。

4）其它接口

```
   1: int clk_notifier_register(struct clk *clk, struct notifier_block *nb);
```

```
   2: int clk_notifier_unregister(struct clk *clk, struct notifier_block *nb);
```

> 这两个notify接口，用于注册/注销 clock rate改变的通知。例如某个driver关心某个clock，期望这个clock的rate改变时，通知到自己，就可以注册一个notify。后面会举个例子详细说明。

```
   1: int clk_add_alias(const char *alias, const char *alias_dev_name, char *id,
```

```
   2:                         struct device *dev);
```

> 这是一个非主流接口，用于给某个clk起个别名。无论出于何种原因，尽量不要它，保持代码的简洁，是最高原则！

#### 4. 通用API的使用说明

结合一个例子（摘录自“Documentation/devicetree/bindings/clock/clock-bindings.txt”），说明driver怎么使用clock通用API。

1）首先，在DTS（device tree source）中，指定device需要使用的clock，如下：

```
   1: /* DTS */
```

```
   2: device {
```

```
   3:     clocks = <&osc 1>, <&ref 0>;
```

```
   4:     clock-names = "baud", "register";
```

```
   5: };
```

> 该DTS的含义是：
>
> device需要使用两个clock，“baud”和“regitser”，由clock-names关键字指定；
>
> baud取自“osc”的输出1，register取自“ref”的输出0，由clocks关键字指定。
>
> 那么问题来了，clocks关键字中，<&osc 1>样式的字段是怎么来的？是由clock的provider，也就是底层clock driver规定的（具体会在下一篇文章讲述）。所以使用clock时，一定要找clock driver拿相关的信息（一般会放在“Documentation/devicetree/bindings/clock/”目录下）。

2）系统启动后，device tree会解析clock有关的关键字，并将解析后的信息放在platform\_device相关的字段中。

3）具体的driver可以在probe时，以clock的名称（不提供也行）为参数，调用clk get接口，获取clock的句柄，然后利用该句柄，可直接进行enable、set rate等操作，如下：

```
   1: /* driver */
```

```
   2: int xxx_probe(struct platform_device *pdev)
```

```
   3: {
```

```
   4:         struct clk *baud_clk;
```

```
   5:         int ret; 
```

```
   6:  
```

```
   7:         baud_clk = devm_clk_get(&pdev->dev, “baud”);
```

```
   8:         if (IS_ERR(clk)) {
```

```
   9:                 …
```

```
  10:         } 
```

```
  11:  
```

```
  12:         ret = clk_prepare_enable(baud_clk);
```

```
  13:         if (ret) {
```

```
  14:                 …
```

```
  15:         } 
```

```
  16: }
```

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/)。
