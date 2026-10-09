---
title: "linux内核中的GPIO系统之（4）：pinctrl驱动的理解和总结"
date: 2017-06-27T22:30:11+08:00
url: "/gpio_subsystem/pinctrl-driver-summary.html"
gid: "397"
emlog_type: "blog"
summary: "本站之前的三篇文章 [1][2][3] 介绍了pin controller（对应的pin controller subsystem）、gpio controller（对应的GPIO subsystem）有关的基本概念，包括pin multiplexing、pin configuration等等。本文将基于这些文章，单纯地从pin controller driver的角度（屏蔽掉pinctrl co"
author: "wowo"
category: "GPIO子系统"
category_alias: "gpio_subsystem"
tags: ["Linux", "driver", "GPIO", "subsystem", "pinctrl"]
views: 63493
comment_count: 7
aliases:
  - "/gpio_subsystem/397.html"
  - "/397.html"
---

## 1. 前言

本站之前的三篇文章[1][2][3]介绍了pin controller（对应的pin controller subsystem）、gpio controller（对应的GPIO subsystem）有关的基本概念，包括pin multiplexing、pin configuration等等。本文将基于这些文章，单纯地从pin controller driver的角度（屏蔽掉pinctrl core的实现细节），理解pinctrl subsystem的设计思想，并掌握pinctrl驱动的移植和实现方法。

## 2. pin controller的概念和软件抽象

相信每一个嵌入式从业人员，都知道“pin（管脚）”是什么东西（就不赘述了）。由于SoC系统越来越复杂、集成度越来越高，SoC中pin的数量也越来越多、功能也越来越复杂，这就对如何管理、使用这些pins提出了挑战。因此，用于管理这些pins的硬件模块（pin controller）就出现了。相应地，linux kernel也出现了对应的驱动（pin controller driver）。

Kernel pinctrl core使用struct pinctrl\_desc抽象一个pin controller，该结构的定义如下（先贴在这里，后面会围绕这个抽象一步步展开）：

|  |  |
| --- | --- |
| |  | | --- | | /\* include/linux/pinctrl/pinctrl.h \*/    struct pinctrl\_desc {    const char \*name;    const struct pinctrl\_pin\_desc \*pins;    unsigned int npins;    const struct pinctrl\_ops \*pctlops;    const struct pinmux\_ops \*pmxops;    const struct pinconf\_ops \*confops;    struct module \*owner;    #ifdef CONFIG\_GENERIC\_PINCONF    unsigned int num\_custom\_params;    const struct pinconf\_generic\_params \*custom\_params;    const struct pin\_config\_item \*custom\_conf\_items;    #endif    }; | |

注1：本文后续的描述基于本站“[X Project](/sort/x_project)”所使用的kernel版本[4]。   
注2：本文很多的表述（特别是例子），都是引用kernel的document[5]（写的很好，可以耐心看看）。

#### 2.1 Pin

kernel的pin controller子系统要想管理好系统的pin资源，第一个要搞明白的问题就是：系统中到底有多少个pin？用软件语言来表述就是：要把系统中所有的pin描述出来，并建立索引。这由上面struct pinctrl\_desc结构中pins和npins来完成。

对pinctrl core来说，它只关心系统中有多少个pin，并使用自然数为这些pin编号，后续的操作，都是以这些编号为操作对象。至于编号怎样和具体的pin对应上，完全是pinctrl driver自己的事情。

因此，pinctrl driver需要根据实际情况，将系统中所有的pin组织成一个struct pinctrl\_pin\_desc类型的数组，该类型的定义为：

|  |
| --- |
| /\*\*    \* struct pinctrl\_pin\_desc - boards/machines provide information on their    \* pins, pads or other muxable units in this struct    \* @number: unique pin number from the global pin number space    \* @name: a name for this pin    \* @drv\_data: driver-defined per-pin data. pinctrl core does not touch this    \*/    struct pinctrl\_pin\_desc {    unsigned number;    const char \*name;    void \*drv\_data;    }; |

number和name完全由driver自己决定，不过要遵循有利于代码编写、有利于理解等原则。另外，为了便于driver的编写，可以在drv\_data中保存driver的私有数据结构（可以包含相关的寄存器偏移等信息）。

注3：[5]中有个例子，大家可以参考理解。

#### 2.2 Pin groups

在SoC系统中，有时需要将很多pin组合在一起，以实现特定的功能，例如SPI接口、I2C接口等。因此pin controller需要以group为单位，访问、控制多个pin，这就是pin groups。相应地，pin controller subsystem需要提供一些机制，来获取系统中到底有多少groups、每个groups包含哪些pins、等等。

因此，pinctrl core在struct pinctrl\_ops中抽象出三个回调函数，用来获取pin groups相关信息，如下：

|  |
| --- |
| struct pinctrl\_ops {    int (\*get\_groups\_count) (struct pinctrl\_dev \*pctldev);    const char \*(\*get\_group\_name) (struct pinctrl\_dev \*pctldev,    unsigned selector);    int (\*get\_group\_pins) (struct pinctrl\_dev \*pctldev,    unsigned selector,    const unsigned \*\*pins,    unsigned \*num\_pins);    void (\*pin\_dbg\_show) (struct pinctrl\_dev \*pctldev, struct seq\_file \*s,    unsigned offset);    int (\*dt\_node\_to\_map) (struct pinctrl\_dev \*pctldev,    struct device\_node \*np\_config,    struct pinctrl\_map \*\*map, unsigned \*num\_maps);    void (\*dt\_free\_map) (struct pinctrl\_dev \*pctldev,    struct pinctrl\_map \*map, unsigned num\_maps);    }; |

> get\_groups\_count，获取系统中pin groups的个数，后续的操作，将以相应的索引为单位（类似数组的下标，个数为数组的大小）。
>
> get\_group\_name，获取指定group（由索引selector指定）的名称。
>
> get\_group\_pins，获取指定group的所有pins（由索引selector指定），结果保存在pins（指针数组）和num\_pins（指针）中。
>
> 注4：dt\_node\_to\_map用于将device tree中的pin state信息转换为pin map，具体可参考后面第3章、第4章的介绍。

当然，最终的group信息是由pinctrl driver提供的，至于driver怎么组织这些group，那是driver自己的事情了，[4]中有一个例子，大家可以参考（在编写pinctrl driver的时候直接copy然后rename即可）。

#### 2.3. Pin configuration(对象是pin或者pin group）

2.1和2.2中介绍了pinctrl subsystem中的操作对象（pin or pin group）以及抽象方法。嵌入式系统的工程师都知道，SoC中的管脚有些属性可以配置，例如上拉、下拉、高阻、驱动能力等。pinctrl subsystem使用pin configuration来封装这些功能，具体体现在struct pinconf\_ops数据结构中，如下：

|  |
| --- |
| struct pinconf\_ops {    #ifdef CONFIG\_GENERIC\_PINCONF    bool is\_generic;    #endif    int (\*pin\_config\_get) (struct pinctrl\_dev \*pctldev,    unsigned pin,    unsigned long \*config);    int (\*pin\_config\_set) (struct pinctrl\_dev \*pctldev,    unsigned pin,    unsigned long \*configs,    unsigned num\_configs);    int (\*pin\_config\_group\_get) (struct pinctrl\_dev \*pctldev,    unsigned selector,    unsigned long \*config);    int (\*pin\_config\_group\_set) (struct pinctrl\_dev \*pctldev,    unsigned selector,    unsigned long \*configs,    unsigned num\_configs);    int (\*pin\_config\_dbg\_parse\_modify) (struct pinctrl\_dev \*pctldev,    const char \*arg,    unsigned long \*config);    void (\*pin\_config\_dbg\_show) (struct pinctrl\_dev \*pctldev,    struct seq\_file \*s,    unsigned offset);    void (\*pin\_config\_group\_dbg\_show) (struct pinctrl\_dev \*pctldev,    struct seq\_file \*s,    unsigned selector);    void (\*pin\_config\_config\_dbg\_show) (struct pinctrl\_dev \*pctldev,    struct seq\_file \*s,    unsigned long config);    }; |

> pin\_config\_get，获取指定pin（管脚的编号，由2.1中pin的注册信息获得）当前配置，保存在config指针中（配置的具体含义，只有pinctrl driver自己知道，下同）。
>
> pin\_config\_set，设置指定pin的配置（可以同时配置多个config，具体意义要由相应pinctrl driver解释）。
>
> pin\_config\_group\_get、pin\_config\_group\_set，获取或者设置指定pin group的配置项。
>
> 剩下的是一些debug用的api，不再说明（用得着的时候，再研究也不迟）。

关于pinconf，有一点一定要想明白：

> **kernel pinctrl subsystem并不关心configuration的具体内容是什么，它只提供pin configuration get/set的通用机制，至于get到的东西，以及set的东西，到底是什么，是pinctrl driver自己的事情。后面结合pin map和pin state的介绍（3.2小节），就能更好地理解这种设计了。**

#### 2.4. Pin multiplexing(对象是pin或者pin group)

为了照顾不同类型的产品、不同的应用场景，SoC中的很多管脚可以配置为不同的功能，例如A2和B5两个管脚，既可以当作普通的GPIO使用，又可以配置为I2C0的的SCL和SDA，也可以配置为UART5的TX和RX，这称作管脚的复用（pin multiplexing，简称为pinmux）。kernel pinctrl subsystem使用struct pinmux\_ops来抽象pinmux有关的操作，如下：

|  |
| --- |
| struct pinmux\_ops {    int (\*request) (struct pinctrl\_dev \*pctldev, unsigned offset);    int (\*free) (struct pinctrl\_dev \*pctldev, unsigned offset);    int (\*get\_functions\_count) (struct pinctrl\_dev \*pctldev);    const char \*(\*get\_function\_name) (struct pinctrl\_dev \*pctldev,    unsigned selector);    int (\*get\_function\_groups) (struct pinctrl\_dev \*pctldev,    unsigned selector,    const char \* const \*\*groups,    unsigned \*num\_groups);    int (\*set\_mux) (struct pinctrl\_dev \*pctldev, unsigned func\_selector,    unsigned group\_selector);    int (\*gpio\_request\_enable) (struct pinctrl\_dev \*pctldev,    struct pinctrl\_gpio\_range \*range,    unsigned offset);    void (\*gpio\_disable\_free) (struct pinctrl\_dev \*pctldev,    struct pinctrl\_gpio\_range \*range,    unsigned offset);    int (\*gpio\_set\_direction) (struct pinctrl\_dev \*pctldev,    struct pinctrl\_gpio\_range \*range,    unsigned offset,    bool input);    bool strict;    }; |

注5：function的概念：

- 为了管理SoC的管脚复用，pinctrl subsystem抽象出function的概念，用来表示I2C0、UART5等功能。pin（或者pin group）所对应的function一经确定，它（们）的管脚复用状态也就确定了
- 和2.2中描述的pin group类似，pinctrl core不关心function的具体形态，只要求pinctrl driver将SoC的所有可能的function枚举出来（格式自行定义，不过需要有编号、名称等内容，可参考[5]中的例子），并注册给pinctrl core。后续pinctrl core将会通过function的索引，访问、控制相应的function
- 另外，有一点大家应该很熟悉：在SoC的设计中，同一个function（如I2C0），可能可以map到不同的pin（或者pin group）上

理解了function的概念之后，struct pinmux\_ops中的API就简单了：

> get\_functions\_count，获取系统中function的个数。
>
> get\_function\_name，获取指定function的名称。
>
> get\_function\_groups，获取指定function所占用的pin group（可以有多个）。
>
> set\_mux，将指定的pin group（group\_selector）设置为指定的function（func\_selector）。
>
> request，检查某个pin是否已作它用，用于管脚复用时的互斥（避免多个功能同时使用某个pin而不知道，导致奇怪的错误）。
>
> free，request的反操作。
>
> gpio\_request\_enable、gpio\_disable\_free、gpio\_set\_direction，gpio有关的操作，等到gpio有关的文章中再说明。
>
> strict，为true时，说明该pin controller不允许某个pin作为gpio和其它功能同时使用。

## 3. pinctrl subsystem的控制逻辑

第2章以struct pinctrl\_desc为引子，介绍了pinctrl subsystem中有关pin controller的概念抽象，包括pin、pin group、pinconf、pinmux、pinmux function、等等，相当于从provider的角度理解pinctrl subsystem。那么，问题来了，怎么使用pinctrl subsystem提供的功能控制管脚的配置以及功能复用呢？这看似需要由consumer（例如各个外设的驱动）自行处理，实际上却不尽然：

> 1）前面讲了，由于pinctrl subsystem的特殊性，对于pin configuration以及pin multiplexing而言，要怎么配置、怎么复用，只有pinctrl driver自己知道。同理，各个consumer也是云里雾里，啥都搞不清楚（想象各位编写设备驱动需要用到pinctrl的时候的心情吧！）。
>
> 2）那这样的配置有道理吗？有！记得我们在[6]中提到过，对一个确定的产品来说，某个设备所使用的pinctrl功能（function）、以及所对应的pin（或者pin group）、还有这些pin（或者pin group）的属性配置，基本上在产品设计的时候就确定好了，consumer没必要（也不想）关心技术细节。因此pinctrl driver就要多做一些事情，帮助consumer厘清pin有关资源的使用情况，并在这些设备需要使用的时候（例如probe时），一声令下，将资源准备好。
>
> 3）因此，pinctrl subsystem的设计理念就是：不需要consumer关心pin controller的技术细节，只需要在特定的时候向pinctrl driver发出一些简单的指令，告诉pinctrl driver自己的需求即可（例如我在运行时需要使用这样一组配置，在休眠时使用那样一组配置）。
>
> 4）最后，需求的细节（例如需要使用哪些pin、配置为什么功能、等等），要怎么确定呢？一般是通过machine的配置文件、具体版型的device tree等，告诉pinctrl subsystem，以便在需要的时候使用。

下面小节我们将会根据这些思路，进行更为详细的分析。

#### 3.1 pin state

根据前面的描述，pinctrl driver抽象出来了一些离散的对象：pin（pin group）、function、configuration，并实现了这些对象的控制和配置方式。然后我们回到某一个具体的device上（如SPI2）：

> 该device在某一状态下（如工作状态、休眠状态、等等），所使用的pin（pin group）、pin（pin group）的function和configuration，是唯一确定的。

把上面的话颠倒过来说，就是：

> pin（pin group）以及相应的function和configuration的组合，可以确定一个设备的一个“状态”。

这个状态在pinctrl subsystem中就称作pin state。而pinctrl driver和具体板型有关的部分，需要负责枚举该板型下所有device（当然，特指那些需要pin资源的device）的所有可能的状态，并详细定义这些状态需要使用的pin（或pin group），以及这些pin（或pin group）需要配置为哪种function、哪种配置项。这些状态确定之后，consumer（device driver）就好办了，直接发号施令就行了：

> 喂，pinctrl subsystem，帮忙将我的xxx state激活。

pinctrl subsystem接收到指令后，找到该state的相关信息（pin、function和configuration），并调用pinctrl driver提供的相应API（参考第2章中struct pinctrl\_desc有关的内容），控制pin controller即可。

#### 3.2 pin map

在pinctrl subsystem中，pin state有关的信息是通过pin map收集，相关的数据结构如下：

|  |
| --- |
| /\* include/linux/pinctrl/machine.h \*/  struct pinctrl\_map {    const char \*dev\_name;    const char \*name;    enum pinctrl\_map\_type type;    const char \*ctrl\_dev\_name;    union {    struct pinctrl\_map\_mux mux;    struct pinctrl\_map\_configs configs;    } data;    }; |

> dev\_name，device的名称。
>
> name，pin state的名称。
>
> ctrl\_dev\_name，pin controller device的名字。
>
> type，该map的类型，包括PIN\_MAP\_TYPE\_MUX\_GROUP（配置管脚复用）、PIN\_MAP\_TYPE\_CONFIGS\_PIN（配置pin）、PIN\_MAP\_TYPE\_CONFIGS\_GROUP（配置pin group）、PIN\_MAP\_TYPE\_DUMMY\_STATE（不需要任何配置，仅仅为了表示state的存在。
>
> data，该map需要用到的数据项，是一个联合体，如果map的类型是PIN\_MAP\_TYPE\_CONFIGS\_GROUP，则为struct pinctrl\_map\_mux类型的变量；如果map的类型是PIN\_MAP\_TYPE\_CONFIGS\_PIN或者PIN\_MAP\_TYPE\_CONFIGS\_GROUP，则为struct pinctrl\_map\_configs类型的变量。

struct pinctrl\_map\_mux的定义如下：

|  |
| --- |
| struct pinctrl\_map\_mux {    const char \*group;    const char \*function;    }; |

> group，group的名字，指明该map所涉及的pin group。
>
> function，function的名字，表示该map需要将group配置为哪种function。

struct pinctrl\_map\_configs的定义如下：

|  |
| --- |
| struct pinctrl\_map\_configs {    const char \*group\_or\_pin;    unsigned long \*configs;    unsigned num\_configs;    }; |

> group\_or\_pin，pin或者pin group的名字。
>
> configs，configuration数组，指明要将该group\_or\_pin配置成“神马样子”。
>
> num\_configs，配置项的个数。
>
> 注6：讲到这里，应该理解为什么2.3小结中struct pinconf\_ops中的api，都不知道configuration到底是什么东西了吧？因为都是pinctrl driver自己安排好的，自产自销，外人（pinctrl subsystem以及consumers）没必要理解！

最后，某一个device的某一种pin state，可以由多个不同类型的map entry组合而成，举例如下[5]：

|  |
| --- |
| static struct pinctrl\_map mapping[] \_\_initdata = {    PIN\_MAP\_MUX\_GROUP("foo-i2c.0", PINCTRL\_STATE\_DEFAULT, "pinctrl-foo", "i2c0", "i2c0"),    PIN\_MAP\_CONFIGS\_GROUP("foo-i2c.0", PINCTRL\_STATE\_DEFAULT, "pinctrl-foo", "i2c0", i2c\_grp\_configs),    PIN\_MAP\_CONFIGS\_PIN("foo-i2c.0", PINCTRL\_STATE\_DEFAULT, "pinctrl-foo", "i2c0scl", i2c\_pin\_configs),    PIN\_MAP\_CONFIGS\_PIN("foo-i2c.0", PINCTRL\_STATE\_DEFAULT, "pinctrl-foo", "i2c0sda", i2c\_pin\_configs),    }; |

> 这是一个mapping数组，包含4个map entry，定义了"foo-i2c.0"设备的一个pin state（PINCTRL\_STATE\_DEFAULT，"default"），该state由一个PIN\_MAP\_TYPE\_MUX\_GROUP entry、一个PIN\_MAP\_TYPE\_CONFIGS\_GROUP entry以及两个PIN\_MAP\_TYPE\_CONFIGS\_PIN entry组成（这些entry的具体含义，大家可参考[5]以及相应的source code理解，这里不再详细说明）。

#### 3.3 通过dts生成pin map

在旧时代，kernel的bsp工程师需要在machine有关的代码中，静态的定义pin map数组（类似于3.2小节中的例子），这一个非常繁琐且不易维护的过程。不过当kernel引入device tree之后，事情就简单了很多：

> pinctrl driver确定了pin map各个字段的格式之后，就可以在dts文件中维护pin state以及相应的mapping table。pinctrl core在初始化的时候，会读取并解析dts，并生成pin map。
>
> 而各个consumer，可以在自己的dts node中，直接引用pinctrl driver定义的pin state，并在设备驱动的相应的位置，调用pinctrl subsystem提供的API，active或者deactive这些state。

至于dts中pin map描述的格式是什么，则完全由pinctrl driver自己决定，因为，最终的解析工作（dts to map）也是它自己做的（具体可参考后面第4章的介绍）。

## 4. pinctrl subsystem的整体流程

通过前面几章的分析，我们对pinctrl subsystem有了一个比较全面的认识，这里以pinctrl整个使用流程为例，简单的总结一下。

1）pinctrl driver根据pin controller的实际情况，实现struct pinctrl\_desc（包括pin/pin group的抽象，function的抽象，pinconf、pinmux的operation API实现，dt\_node\_to\_map的实现，等等），并注册到kernel中。

2）pinctrl driver在pin controller的dts node中，根据自己定义的格式，描述每个device的所有pin state。大致的形式如下（具体可参考kernel中的代码，照葫芦总能画出来瓢~~~）：

> pinctrl\_xxx { /\* the dts node for pin controller \*/   
> ...   
> xxx\_state\_xxx: xxx\_xxx { /\* dts node for xxx device's "xxx state" \*/   
> xxx\_pinmux { /\* pinmux entry \*/   
> xxx = xxxx;   
> xxx = xxxxxxx;   
> ...   
> };   
> xxx\_pinconf { /\* pinconf entry \*/   
> xxx = xxxx;   
> xxx = xxxxxxx;   
> ...   
> };   
> xxx\_pinconf {   
> xxx = xxxx;   
> xxx = xxxxxxx;   
> ...   
> };   
> ...   
> };   
> ...   
> };

3）相应的consumer driver可以在自己的dts node中，引用pinctrl driver所定义的pin state，例如：

> xxx\_device: [xxx@xxxxxxxx](mailto:xxx@xxxxxxxx) {   
> compatible = "xxx,xxxx";   
> ...   
> pinctrl-names = "default";   
> pinctrl-0 = <&xxx\_state\_xxx>;   
> ...   
> };

4）consumer driver在需要的时候，可以调用pinctrl\_get/devm\_pinctrl\_get接口，获得一个pinctrl handle（struct pinctrl类型的指针）。pinctrl subsystem在pinctrl get的过程中，解析consumer device的dts node，找到相应的pin state，进行调用pinctrl driver提供的dt\_node\_to\_map API，解析pin state并转换为pin map。以driver probe时为例，调用过程如下（大家可以自己去看代码）：

> probe   
> devm\_pinctrl\_get or pinctrl\_get   
> create\_pinctrl(drivers/pinctrl/core.c)   
> pinctrl\_dt\_to\_map(drivers/pinctrl/devicetree.c)   
> dt\_to\_map\_one\_config   
> pctlops->dt\_node\_to\_map

5）consumer获得pinctrl handle之后，可以调用pinctrl subsystem提供的API（例如pinctrl\_select\_state），使自己的某个pin state生效。pinctrl subsystem进而调用pinctrl driver提供的各种回调函数，配置pin controller的硬件。   
注7：具体细节就不再描述了，后续开发pinctrl driver的时候，可以再着重说明。

## 5. 参考文档

[1] [linux内核中的GPIO系统之（1）：软件框架](/gpio_subsystem/io-port-control.html)

[2] [linux内核中的GPIO系统之（2）：pin control subsystem](/gpio_subsystem/pin-control-subsystem.html)

[3] [Linux内核中的GPIO系统之（3）：pin controller driver代码分析](/gpio_subsystem/pin-controller-driver.html)

[4] <https://github.com/wowotechX/linux>

[5] [Documentation/pinctrl.txt](https://github.com/wowotechX/linux/blob/x_integration/Documentation/pinctrl.txt)

[6] [X-006-UBOOT-pinctrl driver移植(Bubblegum-96平台)](/x_project/bubblegum_uboot_pinctrl.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/gpio_subsystem/pinctrl-driver-summary.html)。
