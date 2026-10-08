---
title: "Linux的时钟"
date: 2017-05-17T18:55:56+08:00
url: "/timer_subsystem/clock-id-in-linux.html"
gid: "392"
emlog_type: "blog"
summary: "时钟或者钟表（clock）是一种计时工具，每个人都至少有一块，可能在你的手机里，也可能佩戴在你的手腕上。如果Linux也是一个普通人的话，那么她的手腕上应该有十几块手表，包括：CLOCK_REALTIME、CLOCK_MONOTONIC、CLOCK_PROCESS_CPUTIME_ID、CLOCK_THREAD_CPUTIME_ID、CLOCK_MONOTONIC_RAW、CLOCK_REALTI"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["clock"]
views: 24994
comment_count: 26
aliases:
  - "/timer_subsystem/392.html"
  - "/392.html"
---

一、前言

时钟或者钟表（clock）是一种计时工具，每个人都至少有一块，可能在你的手机里，也可能佩戴在你的手腕上。如果Linux也是一个普通人的话，那么她的手腕上应该有十几块手表，包括：CLOCK\_REALTIME、CLOCK\_MONOTONIC、CLOCK\_PROCESS\_CPUTIME\_ID、CLOCK\_THREAD\_CPUTIME\_ID、CLOCK\_MONOTONIC\_RAW、CLOCK\_REALTIME\_COARSE、CLOCK\_MONOTONIC\_COARSE、CLOCK\_BOOTTIME、CLOCK\_REALTIME\_ALARM、CLOCK\_BOOTTIME\_ALARM、CLOCK\_TAI。本文主要就是介绍Linux内核中的形形色色的“钟表”。

二、理解Linux中各种clock分类的基础

既然本文讲Linux中的计时工具，那么我们首先面对的就是“什么是时间？”，这个问题实在是太难回答了，因此我们这里就不正面回答了，我们只是从几个侧面来窥探时间的特性，而时间的本质就留给物理学家和哲学家思考吧。

1、如何度量时间

时间往往是和变化相关，因此人们往往喜欢使用有固定周期变化规律的运动行为来定义时间，于是人们把地球围自转一周的时间分成24份，每一份定义为一个小时，而一个小时被平均分成3600份，每一份就是1秒。然而，地球的运动周期不是那么稳定，怎么办？多测量几个，平均一下嘛。

虽然通过天体的运动定义了秒这样的基本的时间度量单位，但是，要想精确的表示时间，我们依赖一种有稳定的周期变化的现象。上一节我们说过了：地球围绕太阳运转不是一个稳定的周期现象，因此每次观察到的周期不是固定的（当然都大约是24小时的样子），用它来定义秒多少显得不是那么精准。科学家们发现铯133原子在能量跃迁时候辐射的电磁波的振荡频率非常的稳定（不要问我这是什么原理，我也不知道），因此被用来定义时间的基本单位：秒（或者称之为原子秒）。

2、Epoch

定义了时间单位，等于时间轴上有了刻度，虽然这条代表时间的直线我们不知道从何开始，最终去向何方，我们终归是可以把一个时间点映射到这条直线上了。甚至如果定义了原点，那么我们可以用一个数字（到原点的距离）来表示时间。

如果说定义时间的度量单位是技术活，那么定义时间轴的原点则完全是一个习惯问题。拿出你的手表，上面可以读出2017年5月10，23时17分28秒07毫秒……作为一个地球人，你选择了耶稣诞辰日做原点，讲真，这弱爆了。作为linuxer，你应该拥有这样的一块手表，从这个手表上只能看到一个从当前时间点到linux epoch的秒数和毫秒数。Linux epoch定义为1970-01-01 00:00:00 +0000 (UTC)，后面的这个UTC非常非常重要，我们后面会描述。

除了wall time，linux系统中也需要了解系统自启动以来过去了多少的时间，这时候，我们可以把钟表的epoch调整成系统的启动时间点，这时候获取系统启动时间就很容易了，直接看这块钟表的读数即可。

3、时间调整

记得小的时候，每隔一段时间，老爸的手表总会慢上一分钟左右的时间，也是他总是在7点钟，新闻联播之前等待那校时的最后一响。一听到“刚才最后一响是北京时间7点整”中那最后“滴”的一声，老爸也把自己的手表调整成为7点整。对于linux系统，这个操作类似clock\_set接口函数。

类似老爸机械表的时间调整，linux的时间也需要调整，机械表的发条和齿轮结构没有那么精准，计算机的晶振亦然。前面讲了，UTC的计时是基于原子钟的，但是来到Linux内核这个场景，我们难道要为我们的计算机安装一个原子钟来计时吗？当然可以，如果你足够有钱的话。我们一般人的计算机还是基于系统中的本地振荡器来计时的，虽然精度不理想，但是短时间内你也不会有太多的感觉。当然，人们往往是向往更精确的计时（有些场合也需要），因此就有了时间同步的概念（例如NTP（Network Time Protocol））。

所谓时间同步其实就是用一个精准的时间来调整本地的时间，具体的调整方式有两种，一种就是直接设定当前时间值，另外一种是采用了润物细无声的形式，对本地振荡器的输出进行矫正。第一种方法会导致时间轴上的时间会向前或者向后的跳跃，无法保证时间的连续性和单调性。第二种方法是对时间轴缓慢的调整（而不是直接设定），从而保证了连续性和单调性。

4、闰秒（leap second）

通过原子秒延展出来的时间轴就是TAI（International Atomic Time）clock。这块“表”不管日出、日落，机械的按照ce原子定义的那个秒在推进时间。冷冰冰的TAI clock虽然精准，但是对人类而言是不友好的，毕竟人还是生活在这颗蓝色星球上。而那些基于地球自转，公转周期的时间（例如GMT）虽然符合人类习惯，但是又不够精确。在这样的背景下，UTC（Coordinated Universal Time）被提出来了，它是TAI clock的基因（使用原子秒），但是又会适当的调整（leap second），满足人类生产和生活的需要。

OK，至此，我们了解了TAI和UTC两块表的情况，这两块表的发条是一样的，按照同样的时间滴答（tick，精准的根据原子频率定义的那个秒）来推动钟表的秒针的转动，唯一不同的是，UTC clock有一个调节器，在适当的时间，可以把秒针向前或者向后调整一秒。

TAI clock和UTC clock在1972年进行了对准（相差10秒），此后就各自独立运行了。在大部分的时间里，UTC clock跟随TAI clock，除了在适当的时间点，realtime clock会进行leap second的补偿。从1972年到2017年，已经有了27次leap second，因此TAI clock的读数已经比realtime clock（UTC时间）快了37秒。换句话说，TAI和UTC两块表其实可以抽象成一个时间轴，只不过它们之间有一个固定的偏移。在1972年，它们之间的offset是10秒，经过多年的运转，到了2017年，offset累计到37秒，让我静静等待下一个leap second到了的时刻吧。

5、计时范围

有一类特殊的clock称作秒表，启动后开始计时，中间可以暂停，可以恢复。我们可以通过这样的秒表来记录一个人睡眠的时间，当进入睡眠状态的时候，按下start按键开始计时，一旦醒来则按下stop，暂停计时。linux中也有这样的计时工具，用来计算一个进程或者线程的执行时间。

6、时间精度

时间是连续的吗？你眼中的世界是连续的吗？看到窗外清风吹拂的树叶的时候，你感觉每一个树叶的形态都被你捕捉到了。然而，未必，你看急速前进的汽车的轮胎的时候，感觉车轮是倒转的。为什么？其实这仅仅是因为我们的眼睛大约是每秒15～20帧的速度在采样这个世界，你看到的世界是离散的。算了，扯远了，我们姑且认为时间的连续的，但是Linux中的时间记录却不是连续的，我们可以用下面的图片表示：

[![time-sample](/content/uploadfile/201705/94ff6ac23fe58e532aa5c373cef2430520170517105555.gif "time-sample")](/content/uploadfile/201705/4e10109636cbf40837f52aa2565816ce20170517105545.gif)

系统在每个tick到来的时候都会更新系统时间（到linux epoch的秒以及纳秒值记录），当然，也有其他场景进行系统时间的更新，这里就不赘述了。因此，对于linux的时间而言，它是一些离散值，是一些时间采样点的值而已。当用户请求时间服务的时候，例如获取当前时间（上图中的红线），那么最近的那个Tick对应的时间采样点值再加上一个当前时间点到上一个tick的delta值就精准的定位了当前时间。不过，有些场合下，时间精度没有那么重要，直接获取上一个tick的时间值也基本是OK的，不需要校准那个delta也能满足需求。而且粗粒度的clock会带来performance的优势。

7、睡觉的时候时间会停止运作吗？

在现实世界提出这个问题会稍显可笑，鲁迅同学有一句名言：时间永是流逝，街市依旧太平。但是对于Linux系统中的clock，这个就有现实的意义了。比如说clock的一个重要的派生功能是创建timer（也就是说timer总是基于一个特定的clock运作）。在一个5秒的timer超期之前，系统先进入了suspend或者关机状态，这时候，5秒时间到达的时候，一般的timer都不会触发，因为底层的clock可能是基于一个free running counter的，在suspend或者关机状态的时候，这个HW counter都不再运作了，你如何期盼它能唤醒系统，来执行timer expired handler？但是用户还是有这方面的实际需求的，最简单的就是关机闹铃。怎么办？这就需要一个特别的clock，能够在suspend或者关机的时候，仍然可以运作，推动timer到期触发。

三、Linux下的各种clock总结

在linux系统中定义了如下的clock id：

> #define CLOCK\_REALTIME 0   
> #define CLOCK\_MONOTONIC 1   
> #define CLOCK\_PROCESS\_CPUTIME\_ID 2   
> #define CLOCK\_THREAD\_CPUTIME\_ID 3   
> #define CLOCK\_MONOTONIC\_RAW 4   
> #define CLOCK\_REALTIME\_COARSE 5   
> #define CLOCK\_MONOTONIC\_COARSE 6   
> #define CLOCK\_BOOTTIME 7   
> #define CLOCK\_REALTIME\_ALARM 8   
> #define CLOCK\_BOOTTIME\_ALARM 9   
> #define CLOCK\_SGI\_CYCLE 10 /\* Hardware specific \*/   
> #define CLOCK\_TAI 11

CLOCK\_PROCESS\_CPUTIME\_ID和CLOCK\_THREAD\_CPUTIME\_ID这两个clock是专门用来计算进程或者线程的执行时间的（用于性能剖析），一旦进程（线程）被切换出去，那么该进程（线程）的clock就会停下来。因此，这两种的clock都是per-process或者per-thread的，而其他的clock都是系统级别的。

根据上面一章的各种分类因素，我们可以将其他clock总结整理如下：

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
|  | leap second？ | clock set？ | clock tunning？ | original point | resolution | active in suspend？ |
| realtime | yes | yes | yes | Linux epoch | ns | no |
| monotonic | yes | no | yes | Linux epoch | ns | no |
| monotonic raw | yes | no | no | Linux epoch | ns | no |
| realtime coarse | yes | yes | yes | Linux epoch | tick | no |
| monotonic coarse | yes | no | yes | Linux epoch | tick | no |
| boot time | yes | no | yes | machine start | ns | no |
| realtime alarm | yes | yes | yes | Linux epoch | ns | yes |
| boottime alarm | yes | no | yes | machine start | ns | yes |
| tai | no | no | no | Linux epoch | ns | no |

*原创文章，转发请注明出处。蜗窝科技*
