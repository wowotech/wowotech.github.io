---
title: "蓝牙协议中LQ和RSSI的原理及应用场景"
date: 2014-03-12T15:59:46+08:00
url: "/bluetooth/lqi_rssi.html"
gid: "17"
emlog_type: "blog"
summary: "LQI (Link Quality Indication)，是 当前接收到的信号的质量 的一种度量。所谓的接收到信号的质量，是接收器通过 接收到的信号和理想信号之间的错误累积值 估算的。例如，如果使用FSK或者GFSK调制方式，接收器可以将每个bit的频率和期望的频率比较，累积一定数量的symbols（例如64个），就得到了错误累积值。由此可知，由于LQI的测量和调制方式有关，因此它可以相对地给出"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "LQI", "RSSI"]
views: 33851
comment_count: 9
aliases:
  - "/bluetooth/17.html"
  - "/17.html"
---

在蓝牙协议栈的物理层，有这样两个比较有用的参数：LQI和RSSI。它们都是通过接收端，判断当前无线环境的质量（链路质量），以指导后续的动作。但这两个数值的计算原理和使用场景又有很大的差别。

LQI (Link Quality Indication)，是**当前接收到的信号的质量**的一种度量。所谓的接收到信号的质量，是接收器通过接收到的信号和理想信号之间的错误累积值估算的。例如，如果使用FSK或者GFSK调制方式，接收器可以将每个bit的频率和期望的频率比较，累积一定数量的symbols（例如64个），就得到了错误累积值。由此可知，由于LQI的测量和调制方式有关，因此它可以相对地给出当前的链路质量（质量越好，LQI的值越小，反之越大）。

RSSI（Received Signal Strength Indication），是**信号强度**的指示，而不关心信号的质量（quality）或者正确率（correctness）。LQI不关心实际的信号强度，但信号质量却和信号强度有关，因为越强的信号，越不容易受到干扰，在接收端的表现就是“正确率”较高、LQI较低、信号质量较好。

下面用一些典型的场景来说明LQI和RSSI的应用：

- 信号较弱，noise较强的时候，RSSI低、LQI高
- 信号较弱，但基本没有noise时，RSSI低、LQI低
- 非常强的noise（例如干扰器），可以造成高RSSI、高LQI（也就是说，RSSI高也不说明信号一定好）
- 信号非常强，noise较低，RSSI高、LQI低
- 如果信号过强（导致接收饱和），也可能造成高RSSI和高LQI

注：如果你熟悉Linux的Bluez，可以通过如下命令查看LQI和RSSI：

```
 1: hcitool rssi <BT ADDR>
```

```
 2: hcitool lq <BT ADDR>
```

参考文献：[http://e2e.ti.com/support/low\_power\_rf/w/design\_notes/calculation-and-usage-of-lqi-and-rssi.aspx](http://e2e.ti.com/support/low_power_rf/w/design_notes/calculation-and-usage-of-lqi-and-rssi.aspx "http://e2e.ti.com/support/low_power_rf/w/design_notes/calculation-and-usage-of-lqi-and-rssi.aspx")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/lqi_rssi.html)。*
