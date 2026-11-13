# Actual end-to-end scientific answers

Six complete real-source query-to-answer traces follow. The machine-readable version also includes every exact context statement, path, citation and blank review field: `artifacts/phase3c_real_context_representative_traces_v11.json`. Full 60-query traces: `artifacts/phase3c_real_context_answers_v10.json`.

## What did NASA observe about PMMA combustion?

QueryIntentV2 constraints: `[{"relation": "hasMaterial", "entity_id": "PMMA"}]`; requested classes: `['ReportedObservation']`. Effective gravity policy: `{'enabled': True, 'explicit_values': [], 'comparative': False, 'default_preference': ['microgravity'], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['context:bass-film-observation', 'context:bass-flight-rod-observation', 'context:bass-ground-rod-observation', 'context:saffire-iv-flow-observation']. RELATED: []. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.
Research preference: microgravity. Experimental conditions are established by the cited sources.

## Applicable scientific context

- material: PMMA; applies to context:saffire-iv-flow-observation. The group statement and verified membership establish applicability [E-context-3b27486ede2bf8151a2f, E-context-d1e50788b120206316a0].
- gravity: microgravity; applies to context:bass-flight-rod-observation, context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
  Exceptions: context:bass-ground-rod-observation
- material: PMMA; applies to context:bass-flight-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- gravity: normal-gravity; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- oxygen: 21%; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd].
- gravity: microgravity; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- apparatus: context:bass-wind-tunnel; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-5227141f2aaa7feb2e37, E-context-e6623c40985279bec3b2].

## Direct evidence

- context:bass-film-observation [E-context-5227141f2aaa7feb2e37, E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:bass-flight-rod-observation [E-context-5227141f2aaa7feb2e37, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:bass-ground-rod-observation [E-context-5227141f2aaa7feb2e37, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:saffire-iv-flow-observation [E-context-80d7fc00aae08504c315, E-context-d1e50788b120206316a0]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Reported observations

- Sequence of top views showing radiative quenching when
flow velocity goes below 2 cm/s.

Flame nearing blow off extinction as the flow
velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Topical statement selection does not establish every requested experimental condition
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Topical statement selection does not establish every requested experimental condition
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Topical statement selection does not establish every requested experimental condition
- The fire didn’t extinguish and began to grow when we 
turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Topical statement selection does not establish every requested experimental condition

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Spacecraft Fire Safety Needs for Exploration — PDF page 16, table None, row None: For the Saffire-IV PMMA sample, we turned off the 
flow for 20 seconds [E-context-3b27486ede2bf8151a2f]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): nearly spherical bead 4-5 mm in diameter, shown near the right-hand
end of Figure 11.
E. FLAME SPREAD RATES AND LENGTHS
The 35 mm photographic sequences provided the better resolution of the flame structure,
particularly where precise ViSualiZatiOn of the leading blue edge of the flame (essentially invisible in the
638
video record) was needed.
Thus while lacking the time resolution of the video record, the still
photographs were used to obtain the flame spread rates of tests WIF-A,B, and D. Flame position data
from these measurements are shown in Figure 12.
We estimate that the error in each position
measurement is less than 0.01 cm, which in the propagation of error analysis[5] indicates an uncertainty
in the spread rate measurement of less than 0.001 cdsec. The spread rate results are summarized in
Table 1.
F. MICROGRAVITY OPPOSED FLOW.
The measured spread rates for the two opposed-flow cases differ by only 6%, having values of
0.070 and 0.066 cm/sec for WIF-B and WIF-D respectively. Sample heating just prior to ignition (see
also Figure 4 B and D) left the insulation temperature higher in the WIF-B test than in the WIF-D test.
Higher bulk fuel temperatures reduce fuel preheating requirements and may explain the faster flame
spread ratel6].
0. MICROGRAVITY CONCURRENT FLOW.
In concurrent flow, WIF-A, the visible downstream tip of the flame spread at 0.16 cm/sec; while
the base of the flame (where the flame is stabilized and the fuel burnout occurs) spread at 0.12 cm/sec..
The length of the flame therefore grew slowly throughout the test at about 0.04 cmkec. Thus even in the
extended test time provided by the glovebox this fuel did not reach an equilibrium flame length in a
concurrent flow.
While steady flame lengths and propagation rates in concurrent flow have been
predictedi7Iit is not clear what length of WIF-type fuel would be required to observe steady propagation.
H. NORMAL GRAVITY.
Flame spreading tests of the WIF fuel were performed in normalgravity, ignited either at the
sample top or at the bottom, to observe buoyant opposed or concurrent flows (respectively) interacting
with the flame. Tests were also conducted in a horizontal configuration. Still photographs and video
images were recorded during these tests for direct comparison with the WIF results. The molten fuel
frequently dripped in all the normal gravity tests, and the dripped fuel was collected and weighed. A
summary of the flame spread rates, averaged over multiple tests, is shown in Table 2.
I. COMPARISON OF CONCURRENT FLOW RESULTS.
The spreading of the flame tip in the upward case was too rapid to measure in the images
obtained, i.e. the flame length exceeded the length of the fuel sample within about three seconds.
Additionally, small cross currents in the laboratory air perturbed the flame symmetry with respect to the
639
fuel. The data imply an upward flame spread rate of at least several centimeters per second for samples
of this size, compared to the WIF-A result of 0.16 cm/sec. The flame spreading and fuel heating
processes were in many ways not comparable to the microgravity concurrent forced-flow case of WIF-A.
The speeds of the fuel burnout front in the normal-gravity upward test and the WIF-A concurrent
flow test were similar (0.13 and 0.12 cm/sec, respectively). The molten fuel in the case of the WIF-A
experiment accumulated as described above, and the burnout front propagated at a rate controlled by
the rates of fuel melting and fuel vaporization. In the normalgravity upward burning case, however, the
burnout front propagation is strongly influenced by dripping, losing approximately 1/3 of the total fuel
mass over the entire test. The similar WIF and normal gravity burnout rates therefore appear to be
coincidental.
J. COMPARISON OF OPPOSED FLOW RESULTS.
The downward spreading experiments provide a closer comparison between normal-gravity and
microgravity spreading. The microgravity spread rate in a low-speed opposed flow, 0.07 cmlsec, is
muc [E-13fb7f02cdca2f8a]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): t on
orbit. We documented deserts and we looked at dust storms coming over the Atlantic off the coast of
Africa. Any time you take over 4000 pictures on a flight it is a little difficult to find all the best ones to
show. But certainly, this gives you a little flavor of the view we had from orbit.
This flight ended over a year ago from now. Here we look at the data and we are looking at the
future of where we are going. We have been through some rather interesting months on the space
station and I do not need to tell you that. What it means is we are going through a reorganization. We
are going through a restructuring. But the intent is to continue on a space station track and to put a US
space station up there and to provide a platform for you to continue research. Interjected in all of this is
something that we have been working on for the last several months: an interim opportunity to work with
the Russians on the MIR. We will be flying the first cosmonaut on the Space Shuttle on STS-60, Sergei
Krikalev, and then we will be flying a second cosmonaut on STS-63, Vladimir Titov. We are going to be
putting an astronaut on the MIR in early '95. We will be docking the Shuttle to the MIR-1 in mid-95.
There is a plan for follow on flights. There are some opportunities to do some research in the biomedical
and life sciences area, and then the microgravity area. Bob Rhome will enlighten the microgravity
community and will be talking with some of you about what these potential opportunities are. The US
and Russians are currently engaged in negotiations to end somewhere around November 1 to determine
to what extent we will participate together in the International Space Station. Where we are going on that
is not easy to say. We have a lot of unknowns at this point, but I think what is important is for everybody
to remember the big picture; where the vision is. The research itself is important and we do not have
exploration without research, regardless of what may be the prevailing concepts; life support systems
require research. I have read articles about going to Mars and taking indigenous materials. Making
materials is going to require research especially because Mars has one-third Earth gravity. We need to
focus on the future and keep the path going. There are a lot of pictures in this museum and one of my
favorites is of Robert Goddard because he was a rather unique individual. When I was getting ready for
this mission, I know that a lot of people thought that maybe I was a little driven but I want you to know it
was hard not to be. I would go to bed at night and dream about the mission. I know a lot of you did too.
Only I would dream about day one or day five and how it ought to look. I saw a lot of problems in my
dreams and I was never embarrassed about that because I figured Robert Goddard never was. Y U go
O
out to the Goddard Space Flight Center and read the plaque out there and it says "Who is to say what
impossible, for it i the dreams of yesterday that are the hopes of today that are the realities of
s
tomorrow." I had an opportunity to work this mission starting in 1988 and I want to thank everyone of You
for helping my dreams come true.
938
INTERNATIONAL FLIGHT ACCELEROMETER DATA BASE
The International Flight Accelerometer Data Base is a collection O data on flight accelerometers and
f
acceleration measurement systems captured in an Excel spreadsheet. The custom software can be
used on IBM, IBM-compatible, and Macintosh personal computers. The data base currently contains
data on the following accelerometers and acceleration measurementsystems:
Accelerometer Name
Country
MASER Q-flex Accelerometers
Europe
General Active Micromotion Attenuator (GAMMA)
France
Micro AcceIerometer
France
MICROMEDY
France
SPOT3 On-ground Microvibrations Test
France
D-1-MEDEA-ACC
Germany
Microgravity Measurement System (MMS) [EURECA]
Germany
Microgravity Measurement Assembly (MMA) for Spacelab D-2
Germany
Microgravity Measuring Assembly (MMA)
G [E-1f129c9ecb7f6b59]
- Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA — recorded page 1 (physical PDF page unverified): Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA
Maria Thomsena,∗, Carlos Fernandez-Pelloa, Gary A. Ruffb and David L. Urbanb
aDepartment of Mechanical Engineering, University of California - Berkeley, Berkeley,
CA, 94720, USA
bNASA Glenn Research Center, 21000 Brookpark Rd., Cleveland, OH, 44135, USA
*
Corresponding Author (maria.thomsen@berkeley.edu; +1 (510) 701-8170)
Abstract
The flammability of combustible materials in a spacecraft is important for fire safety applications
because the conditions in spacecraft environments differ from those on earth. Experimental testing in
space is difficult and expensive. However, reducing buoyancy by decreasing ambient pressure is a
possible approach to simulate on-earth the burning behavior inside spacecraft environments. The
objective of this work is to determine that possibility by studying the effect of pressure on concurrent
flame spread, and by comparison with microgravity data, observe up to what point low-pressure can
be used to replicate flame spread characteristics observed in microgravity. Specifically, this work
studies the effect of pressure and microgravity on upward/concurrent flame spread over 10 mm thick
polymethyl methacrylate (PMMA) slabs. Experiments in normal gravity were conducted over
pressures ranging between 100 and 40 kPa and a forced flow velocity of 200 mm/s. Microgravity
experiments were conducted during NASA’s Spacecraft Fire Experiment (Saffire II), on board the
Cygnus spacecraft at 100 kPa with an air flow velocity of 200 mm/s. Results show that reductions of
pressure slow down the flame spread over the PMMA surface approaching that in microgravity. The
data is correlated in terms of a non-dimensional mixed convection analysis that describes the
convective heat transferred from the flame to the solid, and the primary mechanism controlling the
spread of the flame. The extrapolation of the correlation to low pressures predicts well the flame
spread rate obtained in microgravity in the Saffire II experiments. Similar results were obtained by
the authors with similar experiments with a thin composite cotton/fiberglass fabric (published
elsewhere). Both results suggest that reduced pressure can be used to approximately replicate flame
behavior of untested gravity conditions for the burning of thick and thin solids. This work could
provide guidance for potential ground-based testing for fire safety design in spacecraft and space
habitats.
Keywords: Flame spread rate, low pressure, environmental conditions, microgravity, PMMA
1
1. Introduction
Concurrent, or flow assisted, flame spread is particularly relevant in fire safety because it is generally
fast and consequently hazardous. It is for this reason that some material flammability tests use this
mode of flame spread to characterize the fire hazard of combustible materials. For example, NASA
relies on an upward flame spread test [1] to screen materials to be used in spacecraft cabins. A problem
with fire testing of spacecraft materials in normal gravity is that spacecraft fire conditions are very
different from those encountered on earth, particularly at the space exploration atmospheres (SEA) that
NASA is planning in using in future spacecraft. They include microgravity, low velocity flows, and
potentially low pressure (~60 kPa) and elevated oxygen concentration (~34%) [2]. The SEA
atmospheric conditions are designed to reduce preparation time for space walks, while keeping the
partial pressure of oxygen acceptable for human respiration [2,3]. However, because of flame-induced
buoyancy it is very difficult to reproduce on earth the environmental conditions of a spacecraft,
particularly the low velocity flows. The spacecraft ventilation system induces flows with velocities that
are of the order 100 mm/s to 200 mm/s, while the buoyant flow induced by a propagating flame have
velocities of the order of 300 mm/s to 600 mm/s. Thus, fire testing of materials to be used in spacecraft
requires either a red [E-4084124e9dc2a202]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): ng the acceleration. That was not easy. We found a system, finally, that is quite
smooth but that turned out to be one of the serious problems.
Question: What kind of rotational position accuracy do you achieve with the system ?
Answer: The accuracy in the positioning of 2 axis that is on the order of half a degree.
Question: How long does the flipping procedure fake ?
Answer: It takes about 1 second to flip over. We are trying to keep that period short. On the other
hand, it induces vibration and disturbance. That is a compromise between the requirements.
Question: About the performance data, you talked about it. How about some results? Before flight what
does your noise calibration look like ?
Answer: Yes. We tested the system. The task as I said in the beginning, was to measure
g within
very high level of noise. We did the following: We mounted our system on a plate and calibrated that
system by very sensitive quartz actuators and we found resolutions better than
g on ground. After
that calibration process, we mounted a shaker on to that plate, and the shaker excited the plate to about
5 g. Then we repeated our procedure by the actuators and we found the same signal, not affected by the
high vibration level of the sinusoidal vibration with 5g amplitude. We did this with a variable frequency
between 1 Hz and 50 Hz. That is a whole range of frequency we have qualified it for.
867
EURECA MICROGRAVITY ENVIRONMENT
- PRELIMINARY FLIGHT DATA
D. Eilers" and H. R. Stark+
'ERN0 Raumfahmechhnik, Bremen, Germany
+ ESA/ESTEC, Noordwijk, The Netherlands
ABSTRACT
EURECA, the European Retrievable Carrier, provides a new platform to perform microgravity
research in a low gravity orbital environment over extended duration of at least six months. The first
mission was launched in August 1992. After the free flying period, the EURECA spacecraft was
successfully retrieved by the Space Shuttle and landed on June 24, 1993. EURECA has been
designed for at least five launches and retrievals.
In order to comply with the stringent microgravity requirements, the EURECA system,
subsystem and payload performances shall maintain a controlled microgravity environment and shall
not exceed a limited acceleration response spectrum at the payload mechanical interfaces. Intensive
design, development and optimization activities were implemented and verified by simulations,
analyses and during an integrated system test on-ground. finally,
on-board acceleration
measurement system completed the information about the quality of the micro-g environment.
This paper summarizes the preliminary review of the residual accelerations as measured
during the first mission period of EURECA between 07.08.92 end the 1.10.92 in correlation with
the previous analysis and ground test results, as well as some later data.
The on-board Microgravity Measurement Subsystem 1MMS) detected the residual
accelerations after command from ESOC, the European Space Operations Center, in Darmstadt,
Germany. This review is namely based on a set of 906 acceleration measurements during the initial
.
period, with a duration of 3 167 minutes and in some cases up to 657.6 minutes.
The MMS data were transmitted from ESOC to the Microgravity User Support Centre
(MUSCl at DLR, K6ln-Porz, for processing and presentation. The preliminary evaluation provided
very interesting results. For instance, a dominant vibration frequency of 0.85 Hz is observed which
can correspond to a FEM-mode shape. A modulation frequency of 0.04 Hz could also be caused by
two aGacent mode shapes. Measurements over orbit periods show repetitive slight changes in the
vibration behavior beginning with and during each eclbse phase, etc.
The paper will present these findings and the conclusion that the desire design goal for the
microgravity quality on EURECA was met.
Joint Z + l Science Review for USMLl and USMF-1 with the Microgmvity Measurement GmUp, September
22-24, 1993, Huntsville, Alabama, USA.
869
INTRODUCTION
EURECA, as a larg [E-08c3327bddbeb4ae]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): cation Specified From 0.1 Hz To 500 Hz
Acceleration Spectrum At Module-To-Payload Rack Interfaces
756
I .
*
I
I
,.-----
Figure 8 CAL Microgravity Environment Control Concept
SPACECRAFT UllLlUTlON
MISSIONSCENARIOIOTERATIONS
MICRO-G DYNAMICS DISTygeANCE
COHPUTATIONAL XODEL ELEXENTS
Figure 9 Flight Configuration Microgravity Environment Analysis (Microgravity Computational Model)
75 7
Figure 10 Microgravity Environment Dynamic Disturbance Control (Structure-borne And Airborne
Transmission Paths
758
Discussion
Question: How do you calibrate the hammer itself ?
Answer: Now for each hammer you get calibration curves. Each hammer has a serial number and
calibration and hence this is known.
Question: Now, this is on the ground, correct ?
Answer: Yes, this is done on the ground. We use the same hammer on the orbit, of course, to have the
same reference.
Question: So you do not have anything special for space applications ?
Answer: No, we don’t have to. This should be stable for the life of the hammer.
Question: About your data, am you recording jt
or are you pre-windowing it ?
Answer: The hammer was actually hooked up to the MMA. So it was complimentary to the MMA and
by this we got the data also real time to the ground. We used the MMA as such and the hammer was
plugged in and so we got the data down to our ground station. We also got real time feedback about
impact and gave also indication to the astronaut whether it was right or not, whether he should repeat it
or not.
Question: M a t was your sampling rate ?
Answer: We had a sampling rate of 300 samples per second.
Question: What was the range of force you could exert on the structure ?
Answer: We limited the force of the hammer to 200 Newton. But the hammer is able to go out to 1250
Newton
Question: Didyou have a range like increments of 70 Newtons or 20 Newtons ?
Answer: We did a different investigation. Our first loop was to have a constant force and check the
repeatability of one location to the other and also see whether this is valid, whether we have really a
linear structure behavior or whether we have non-linearity in the structure. During the third Cycle W used
e
different levels of force which give us also an indication whether there is linear nature or nonlinear nature
in the structure.
759
Question: It is surprising how repeatable it is. Once you have done a few and you get this comfort zone
you are doing the same thing over and over again. It is amazing. Seems like it is very well controlled ?
Answer: We were surprised too. It was so stable because the object was to hit one location 5 times after
the last with a pause in-between (about 15 seconds).
Comment: Another experiment was to find the difference between the behavior of the structure on
ground and in orbit if any. The dynamic behavior and principle does not include any dependence on g
but the boundary conditions of the system do. My question is what is the difference and if there is one
there is a need for an investigation. That is one point. Stark also did extensive count measurements
after the mission sequence tests when Spacelab was fully integrated. The dynamic system was
equivalent to that in orbit and he is going to compare that data, the flight data, to the ground data. He will
also do lots of modeling to predict the differences if any between ground and orbit.
Question: Obviously you can? really do a true impulse especially in a situation where you can? really
see a certain level of force so you don't dent the spacecrafl. One way to verify that you have truly
excited the frequencies of interest is to do a sinusoidal disturbance on the ground to compare the results
or to put a cushion over the hammer and to give you a signal richer in lower frequency components. Did
you look at that part ?
Answer: Yes, we looked at that in the very beginning when we defined the experiment. There are better
ways to do this, but since we had the MMA it was easy for us just to hook it up to a hammer, with all its
known limita [E-4ee1d5c251e70899]
- The Second International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): e propagating
combustion wave for Reaction (5) .
2500
3500
(K)
Figure 6 The effect of temperature on the calculated
vapor pressues of species present in Reaction (1) to
(4) .
Figure 7 AI 20 3 whisker formation during Reaction (3) .
207
(a)
(b)
Figure 8 (a) Expanded or foamed ceramic an d ce ram ic- metal composites produced by reaction (4)
comparison of reacter (left) with unreacted (right) green pellet ; (b) scanni n'd electron photomicrograph of (a)
for x = o.
Figure 9 Optical photom icrograph of TiC-AI 2 0 3 -9AI composite , indicating
AI to the bottom half of the coposite.
208
g r avi ~ y-driv e n
fluid flow of the liquid
COMMENTS
Question (Pror. Bernard J. Matkowsky, Northwestern Unive rsity): You referred to experiments in the former
Soviet Union, in which the sample produced by S.H.S. is signifIcantly expanded (i.e., its porosity is
signifIcan tly increased). I presume you are referring to the experiments of A. Shteinberg. First, in his
experiments the increase in porosi ty was due to gas being liberated, rather than consumed, in the reaction.
Was this true in your experiments as well? Second, he observed that the degree of increase in porosity was
different if the sample was arranged (1) horizontally or (2) vertically in normal gravity, and (3) in
microgravity. I understand that you have not yet done the experiments in mierogravity, but did you observe
similar differences between horizon tal and vertical arrangements in normal gravity.
Finally, you described the propagation of the combustion wave as being either (1) stable, by which yo u mean
that it propagated with a planar front with a constant velocity, or (2) unstable, by which you mean that
propagation ceased. However, in auuition to the stable moue of propagation, there have been observations
of pulsating propagation, in which a planar front propagates with an oscillatory velocity, and spinning
propagation, in which a hot spot (or spots) moves in a helical fashion . Did you observe either of these
modes of propagation?
Answer: The increase in porosity was due to gaseous species both liberateu and consumed. For example, in
combustion synthesis reactions involving B~OJ' which has a boiling point slightly in excess of 1800 degrees C,
the combustion temperature was well abo\'e this point, and, th erefore, generated B~()J gas of 1 atmosphere
pressure. At the same time, the B~OJ gas was also consumed in the reaction to produce compounds such as
TiB1 with TiB0 1 reactant or B jC with graphite as the reactant. In certain combustion synthesis reactions
that we studied, the combustio / temperature was suffIcient to produce a signifIcant volatility (i.e., partial
pressure of aluminum gas). In this respect. the aluminum gas and the B20 J gas reacteuto produce AI 20 J
whiskers. In our experimen ts, th e \'ery large levels of porosity ( e.g., greater than o r e qual to 75%) were
produced when there was only one major gaseous species produced (i.e., B10 J gas).
Yes, I was referring to Professor Alex Shtcinberg's work in Russia. Most of our experiments were conducted
in which the pellet was ignited at the boltom of the cylindrical pellet and the major expansion occurred in
the vertical direction against gravity.
We uefIned a stable combustion front as one which propagated a steady rate down through the pellet,
where in an unstable combustion front was one which eventually quenched out. Our definition of a semistable combustion front was one that slowed down, almost extinguished, and then picked up speed agai n,
probably going through two or three of these cycles. In one or two occasions we did observe a spin ning
moue of propagation , which we dclined as semi-stable front.
209
-
-
--
SESSION E - PLENARY DINNER
(Chair, Robert Rhome)
Preceding Page Blank
FIRE SAFETY PRACTICES IN THE SHUTTLE AND THE SPACE
STATION FREEDOM
Robert Friedman
NASA Lewis Research Center
Cleveland, Ohio 44135
ABSTRACT
The Shuttle reinforces its policy of fire-preventive measures with onboard smoke detector [E-69974633ab0fed54]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): et polymers there and you
actually extend those polymers and then your viscosity will be at least 3 times that in compressional now,
and that could stabilize you ?
Answer: Well certainly. All of these fluids that we are dealing with are non Newtonian and of course the
theory was developed for Newtonian fluids so right away you have got a problem there. The problem in
trying to do it by extensional flows though, is the fact that without gravity drainage to help pull that out,
you just can't pull a strand. There is just not enough strength, if you will, or whatever it takes in a column
to overcome the inertia and that is why you couldn't just dip a stick in there and pull it out from the stick.
It just doesn't want to pull. So what we were trying to do was to deploy the strand without having to
accelerate the mass of the strand. So that is why we thought, well if we simply lay it out as we go along,
then we will have no inertial forces to overcome or to accelerate and hopefully we will have gotten the
force-free deployment scheme. And of course you can only do that to a certain degree of accuracy by
trying to squeeze it out in your hand. The other problem of course was the silicone oil was sticky and
was always getting in between the guide that Carl was working with, and also, the syringes that we were
trying to work with had a slight taper to them. So they tend to want to hang up and there is a lot of
stidion and it could use a little bit more human engineering. But as it tumed out real well for a first cut
experiment, I think we were able to do a pretty decent experiment. Carl did a beautiful job with the
technique of trying to work that.
Question: In keeping with the bubbles of the morning when you pushed on that syringe was fhefe any
evidence of bubbles being generated ?
Answer: That is interesting. We didn't really see any bubbles. Again, the fluid is very viscous and I
don't know why we didn't really see any. What we tried to do in a couple of cases when Carl didn't get a
string to be pulled very well, he would go back in and try to aspirate the little blob by pulling back on the
syringe. When he did that you always got bubbles in it. But then if you tried to deploy it with bubbles in it
e
you had all sorts of problems because bubbles would come out and cause the thing to break up. But W
did not seem to have problemsjust extruding from the fluid that was in the syringe the first time. If there
were any bubbles in there, I surely did not see any evidence of it. I don't know why there should have
been, come to think of it.
661
Question: When you start considering the low viscosity and low surface tension for certain classes of
optical materials, did you get any insight from what you have done here for how you might consider doing
something like that in micmgavity ?
Answer: Well, yes. The range of viscosity we chose was roughly around 10 kilo centistoke, if you like
that unit, but that is the way they are advertised up to 100,000 centistoke and that is roughly the range.
The 100,000 value is sort of the low end of the optical fibers that you would pull from silicon or silica.
The 10 k was dorm more of what you would expect of the fluoride systems as I understand it. I guess
the conclusion that I would have reached here, was that these were pretty fat fibers and they had to be
fat to last long enough to be measured. I am under the opinion of what I have seen so far, that the
gravity drainage is a very stabilizing effect in pulling fibers and probably you would run into very serious
trouble if you tried to do very thin fibers in microgravity. I am not sure there is an advantage to doing
that from what I have seen so far. I will have to look at that much more carefully before I make a blatant
statement but I guess what I am saying is, you can pull strands a lot easier on Earth than you can in
microgravity because of the gravity drainage effect. Rather than being something that hurts you it
seems to help you.
662
NUCLEATION OF CR [E-a01be685f4e205f1]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — recorded page 1 (physical PDF page unverified): 142 data points have been obtained. A series of ground tests
have also been conducted so that 0-g and 1-g behavior can be compared.
Experimental Results
Figure 1 shows the PMMA surface temperature at the rear stagnation point as a function of
mass flow rate of oxygen (%O2 in flow x ρUA). The open symbols show conditions that selfextinguished. The closed symbols show conditions where the suppressant was applied with the solid
circles indicating flames that were extinguished. The conditions represented by triangles did not
extinguish within the 20 seconds of low-gravity. For O2 flow rates below about 0.7 g/s (velocities
below 5 cm/s for standard air) and surface temperatures below approximately 270 deg C, the flames
extinguished within 20 sec with no addition of suppressant. Increasing either the flow velocity or the
surface temperature allowed the flame to be sustained through the low-gravity period. This result is
similar to that obtained by Goldmeer [1] who showed that increasing the sample temperature made
the flame more difficult to extinguish. On this plot, there is no discernable boundary between flames
that were extinguished by suppressant and those that were not. This is likely the result of the
influence of a number of parameters such a g-jitter, sample pre-heat, flame shape, and duration of
suppressant flow. The effect of these parameters will be the focus of future work.
Figure 2 shows the time-to-extinguish as a function of flow velocity for an oxidizer of rich
air and the suppressant 25% CO2/75% rich air. The time to extinguish plotted in the figure is the
time from when suppressant reached the sample to extinguishment. The images show end views of
the PMMA sample in flowing oxidizer after the flames became stable in low-gravity. At 1 cm/s, the
flame extinguished within 4 sec, primarily because of the weak flame. The time to extinguish
increased at 2 cm/s but was then observed to decrease with increasing velocity. At the higher
velocities, the flame did not wrap completely around the cylinder but was open in the wake region.
The luminosity and thickness of the flame increased with velocity, as did the width of the wake
region where the flame was absent. These results show the interdependence of the flow velocity and
subsequent flame intensity and structure on the suppression behavior. Additional tests are being
conducted using lower CO2 concentrations to elucidate the role of velocity and flame development
on the time to extinguish.
THEORETICAL INVESTIGATION
Due of the limited duration of low gravity on the aircraft and the difficulty in quantifying the
effect of g-jitter on suppression near the extinction boundary, a modeling effort is supporting the
experimental program. A modified version of the Fire Dynamics Simulator (FDS) computer code
[2,3] was used to conduct two-dimensional simulations of ignition and flame spread along
(perpendicular to the axis) a PMMA cylinder. Prior to beginning calculations, the finite volume
radiation solver in the FDS code was modified so that gas-phase radiation was properly accounted
for when the finite rate chemistry model is invoked. This radiation solver determines the radiation
flux on the surface of the PMMA and the divergence of the radiation flux in the gas. The ideal gases
were assumed to be gray and non-sooting. Absorption coefficients for H2O and CO2 were
determined using RadCal [4].
NASA/CP—2003-212376/REV1
302
Following the work of previous researchers, the chemical reaction of MMA vapor generated by
PMMA pyrolysis was modeled using a one-step overall chemical reaction (F + O2 -> CO2 + H2O)
and second-order Arrehnius kinetics [5,6]. Kinetic constants were obtained from Seshandri and
Williams [7]. The specific heats of the gaseous species were assumed constant and equal; molecular
transport coefficients were temperature-dependent [4]. In-depth heat transfer at each surface point on
PMMA solid was modeled using a one-dimensional conduction equation. The net heat flux at  [E-cf90bf6996c63f80]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Approach; https://ntrs.nasa.gov/citations/20160000593 [E-context-5227141f2aaa7feb2e37]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-80d7fc00aae08504c315]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-3b27486ede2bf8151a2f]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-e6623c40985279bec3b2]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Material Ignition and Suppression Test; https://ntrs.nasa.gov/citations/20160000593 [E-context-87d3a70a788ae398fe4a]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-13fb7f02cdca2f8a]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-1f129c9ecb7f6b59]
- Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA — ntrs-20200000557, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20200000557 [E-4084124e9dc2a202]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-08c3327bddbeb4ae]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-4ee1d5c251e70899]
- The Second International Microgravity Combustion Workshop — ntrs-19930010989, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19930010989 [E-69974633ab0fed54]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-a01be685f4e205f1]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — ntrs-20040053504, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20040053504 [E-cf90bf6996c63f80]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-d1e50788b120206316a0]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, PMMA rod comparison; https://ntrs.nasa.gov/citations/20160000593 [E-context-d0e9f6c262d92e57e3bd]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-90f697823c2ba1b2ea82]



## What did NASA observe about PMMA combustion under microgravity?

QueryIntentV2 constraints: `[{"relation": "hasMaterial", "entity_id": "PMMA"}, {"relation": "hasGravityCondition", "entity_id": "microgravity"}]`; requested classes: `['ReportedObservation']`. Effective gravity policy: `{'enabled': True, 'explicit_values': ['microgravity'], 'comparative': False, 'default_preference': [], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['context:bass-film-observation', 'context:bass-flight-rod-observation']. RELATED: ['context:bass-ground-rod-observation', 'context:saffire-iv-flow-observation']. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.

## Applicable scientific context

- material: PMMA; applies to context:saffire-iv-flow-observation. The group statement and verified membership establish applicability [E-context-3b27486ede2bf8151a2f, E-context-d1e50788b120206316a0].
- gravity: microgravity; applies to context:bass-flight-rod-observation, context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
  Exceptions: context:bass-ground-rod-observation
- material: PMMA; applies to context:bass-flight-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- gravity: normal-gravity; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- oxygen: 21%; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd].
- gravity: microgravity; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- apparatus: context:bass-wind-tunnel; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-5227141f2aaa7feb2e37, E-context-e6623c40985279bec3b2].

## Direct evidence

- context:bass-film-observation [E-context-5227141f2aaa7feb2e37, E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2]
  Matches: ['hasMaterial=PMMA', 'hasGravityCondition=microgravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  hasGravityCondition: MATCH; requested: microgravity; actual: ['microgravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:bass-flight-rod-observation [E-context-5227141f2aaa7feb2e37, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd]
  Matches: ['hasMaterial=PMMA', 'hasGravityCondition=microgravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  hasGravityCondition: MATCH; requested: microgravity; actual: ['microgravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
Related evidence: 2 condition groups representing 2 candidates. All candidate IDs and citations remain available in the evidence bundle.

## Related evidence

- context:bass-ground-rod-observation [E-context-5227141f2aaa7feb2e37, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: ['hasGravityCondition=microgravity']; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  hasGravityCondition: DIFFER; requested: microgravity; actual: ['normal-gravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:saffire-iv-flow-observation [E-context-80d7fc00aae08504c315, E-context-d1e50788b120206316a0]
  Matches: ['hasMaterial=PMMA', 'reviewed requested information class']; differs: []; unknown: ['hasGravityCondition=microgravity']; invalid: [].
  hasMaterial: MATCH; requested: PMMA; actual: ['PMMA'].
  hasGravityCondition: UNKNOWN; requested: microgravity; actual: [].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Reported observations

- Sequence of top views showing radiative quenching when
flow velocity goes below 2 cm/s.

Flame nearing blow off extinction as the flow
velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Statement applicability — hasGravityCondition: MATCH; requested: microgravity; established: ['microgravity'].
  Topical statement selection does not establish every requested experimental condition
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Statement applicability — hasGravityCondition: MATCH; requested: microgravity; established: ['microgravity'].
  Topical statement selection does not establish every requested experimental condition
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Statement applicability — hasGravityCondition: DIFFER; requested: microgravity; established: ['normal-gravity'].
  Topical statement selection does not establish every requested experimental condition
- The fire didn’t extinguish and began to grow when we 
turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]
  Statement applicability — hasMaterial: MATCH; requested: PMMA; established: ['PMMA'].
  Statement applicability — hasGravityCondition: UNKNOWN; requested: microgravity; established: [].
  Topical statement selection does not establish every requested experimental condition

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Results of Large-Scale Spacecraft Flammability Tests — Saffire-II terrestrial reference tests: In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.

In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]
- Results of Large-Scale Spacecraft Flammability Tests — Saffire-II silicone results: Results were convincing although rather anticlimactic as none of the silicone samples burned.
When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly
extinguished. The igniters all appeared to function normally and the materials were clearly damaged in
the vicinities of the igniters. [E-context-d86d030e275ce04b8b82]
- Spacecraft Fire Safety Needs for Exploration — PDF page 16, table None, row None: For the Saffire-IV PMMA sample, we turned off the 
flow for 20 seconds [E-context-3b27486ede2bf8151a2f]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): nearly spherical bead 4-5 mm in diameter, shown near the right-hand
end of Figure 11.
E. FLAME SPREAD RATES AND LENGTHS
The 35 mm photographic sequences provided the better resolution of the flame structure,
particularly where precise ViSualiZatiOn of the leading blue edge of the flame (essentially invisible in the
638
video record) was needed.
Thus while lacking the time resolution of the video record, the still
photographs were used to obtain the flame spread rates of tests WIF-A,B, and D. Flame position data
from these measurements are shown in Figure 12.
We estimate that the error in each position
measurement is less than 0.01 cm, which in the propagation of error analysis[5] indicates an uncertainty
in the spread rate measurement of less than 0.001 cdsec. The spread rate results are summarized in
Table 1.
F. MICROGRAVITY OPPOSED FLOW.
The measured spread rates for the two opposed-flow cases differ by only 6%, having values of
0.070 and 0.066 cm/sec for WIF-B and WIF-D respectively. Sample heating just prior to ignition (see
also Figure 4 B and D) left the insulation temperature higher in the WIF-B test than in the WIF-D test.
Higher bulk fuel temperatures reduce fuel preheating requirements and may explain the faster flame
spread ratel6].
0. MICROGRAVITY CONCURRENT FLOW.
In concurrent flow, WIF-A, the visible downstream tip of the flame spread at 0.16 cm/sec; while
the base of the flame (where the flame is stabilized and the fuel burnout occurs) spread at 0.12 cm/sec..
The length of the flame therefore grew slowly throughout the test at about 0.04 cmkec. Thus even in the
extended test time provided by the glovebox this fuel did not reach an equilibrium flame length in a
concurrent flow.
While steady flame lengths and propagation rates in concurrent flow have been
predictedi7Iit is not clear what length of WIF-type fuel would be required to observe steady propagation.
H. NORMAL GRAVITY.
Flame spreading tests of the WIF fuel were performed in normalgravity, ignited either at the
sample top or at the bottom, to observe buoyant opposed or concurrent flows (respectively) interacting
with the flame. Tests were also conducted in a horizontal configuration. Still photographs and video
images were recorded during these tests for direct comparison with the WIF results. The molten fuel
frequently dripped in all the normal gravity tests, and the dripped fuel was collected and weighed. A
summary of the flame spread rates, averaged over multiple tests, is shown in Table 2.
I. COMPARISON OF CONCURRENT FLOW RESULTS.
The spreading of the flame tip in the upward case was too rapid to measure in the images
obtained, i.e. the flame length exceeded the length of the fuel sample within about three seconds.
Additionally, small cross currents in the laboratory air perturbed the flame symmetry with respect to the
639
fuel. The data imply an upward flame spread rate of at least several centimeters per second for samples
of this size, compared to the WIF-A result of 0.16 cm/sec. The flame spreading and fuel heating
processes were in many ways not comparable to the microgravity concurrent forced-flow case of WIF-A.
The speeds of the fuel burnout front in the normal-gravity upward test and the WIF-A concurrent
flow test were similar (0.13 and 0.12 cm/sec, respectively). The molten fuel in the case of the WIF-A
experiment accumulated as described above, and the burnout front propagated at a rate controlled by
the rates of fuel melting and fuel vaporization. In the normalgravity upward burning case, however, the
burnout front propagation is strongly influenced by dripping, losing approximately 1/3 of the total fuel
mass over the entire test. The similar WIF and normal gravity burnout rates therefore appear to be
coincidental.
J. COMPARISON OF OPPOSED FLOW RESULTS.
The downward spreading experiments provide a closer comparison between normal-gravity and
microgravity spreading. The microgravity spread rate in a low-speed opposed flow, 0.07 cmlsec, is
muc [E-13fb7f02cdca2f8a]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — recorded page 1 (physical PDF page unverified):  observed with
paper samples in microgravity.
In normal gravity, delayed
backside ignition was observed
with the PMMA samples in air
under the ceiling configuration
(upward
laser
irradiation
normal to a downward facing
sample surface). This curious
behavior of flame during the
first transition will be further
studied.
Our
numerical
calculation will be used to
understand why such long
delay occurs for the backside
ignition.
Ignition behavior of the PMMA sheet by a CO2 laser in zero gravity and also in normal
gravity was numerically calculated. The details of our model and computational scheme
can be found in our previous publication2. The absorption of the incident laser energy by
the degradation products from PMMA is included in our three-dimensional, timedependent code. The results of ignition delay time (irradiated side) in quiescent normal
Figure 4. Ignition of PMMA(0.2 mm) in
Figure 3. Ignition delay of PMMA (0.2
zero gravity.
mm) thick in quiescent normal gravity.
gravity are shown in Figure 3 as a function of the sample orientation angle. (The sample
orientation angle of 0 degree
means a vertically mounted
configuration and +90 degree
means a horizontal upward
facing sample.)
In this
calculation, the laser beam
irradiates normal to the
sample surface at all angles.
The ignition delay time is the
shortest
at
the
ceiling
configuration (-90 degree) and
it increases with an increase in
sample orientation angle.
However, from about 20
degree to 60 degree ignition
delay time tends to decrease
Figure 5. Ignition of the front PMMA surface (0.2 mm thick)
with the angle. This decrease
followed by ignition of the back surface in microgravity.
is caused by the ignition
location moving toward the
center of the laser beam. On the other hand, in zero microgravity ignition delay time
increases monotonically with an increase in external flow velocity due to blowing away
the ignition location from the irradiated area. Ignition behavior on the front (irradiated)
surface followed by ignition on the backside surface in zero gravity under an external air
flow of 10 cm/s (from right to left) is shown in Figure 5. The calculated results show the
NASA/CP—2003-212376/REV1
127
flow from the backside to the front side through an open hole generated by the absorption
of the laser beam. This flow is generated by the flame on the front surface and this flow
could have significant effects on ignition of the backside surface. We are currently
studying in detail the transition behavior from the front surface ignition to the ignition of
the backside surface.
Effects of the sample thickness on the transitions.
Our numerical code based on the modified version of the Fire Dynamic
Simulation code is being extended to apply to a sample of any thickness, removing the
thermally thin limitation. For the above results described of PMMA, thermal conduction
in the sample is included but not the transport process of the degradation products in the
sample. However, for a paper sample, transport processes of degradation products and
oxygen, and a convective flux based on the Darcy’s law are included to describe the
transport processes in the porous paper sample using a porosity parameter. Preliminary
results of the first transition from localized ignition to flame spread are shown in Figure
Figure 6. Calculated temperature distribution during the transition from localized ignition to
flame spread over a paper based on two case in microgravity, left: thermally thin case and right:
general case under external flow of 20 cm/s from right to left. The sample thickness is expanded.
6. For the thermally thin case (includes heat conduction along the sample), flame and
subsequent flame spreading appears simultaneously on both sample surfaces. However,
for the general case, flame appears at first on the irradiated surface and then on the
backside surface with some delay similar to the PMMA case described above. We are
currently conducting parametric study to determine under what [E-dc10a634dcb57b01]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): et polymers there and you
actually extend those polymers and then your viscosity will be at least 3 times that in compressional now,
and that could stabilize you ?
Answer: Well certainly. All of these fluids that we are dealing with are non Newtonian and of course the
theory was developed for Newtonian fluids so right away you have got a problem there. The problem in
trying to do it by extensional flows though, is the fact that without gravity drainage to help pull that out,
you just can't pull a strand. There is just not enough strength, if you will, or whatever it takes in a column
to overcome the inertia and that is why you couldn't just dip a stick in there and pull it out from the stick.
It just doesn't want to pull. So what we were trying to do was to deploy the strand without having to
accelerate the mass of the strand. So that is why we thought, well if we simply lay it out as we go along,
then we will have no inertial forces to overcome or to accelerate and hopefully we will have gotten the
force-free deployment scheme. And of course you can only do that to a certain degree of accuracy by
trying to squeeze it out in your hand. The other problem of course was the silicone oil was sticky and
was always getting in between the guide that Carl was working with, and also, the syringes that we were
trying to work with had a slight taper to them. So they tend to want to hang up and there is a lot of
stidion and it could use a little bit more human engineering. But as it tumed out real well for a first cut
experiment, I think we were able to do a pretty decent experiment. Carl did a beautiful job with the
technique of trying to work that.
Question: In keeping with the bubbles of the morning when you pushed on that syringe was fhefe any
evidence of bubbles being generated ?
Answer: That is interesting. We didn't really see any bubbles. Again, the fluid is very viscous and I
don't know why we didn't really see any. What we tried to do in a couple of cases when Carl didn't get a
string to be pulled very well, he would go back in and try to aspirate the little blob by pulling back on the
syringe. When he did that you always got bubbles in it. But then if you tried to deploy it with bubbles in it
e
you had all sorts of problems because bubbles would come out and cause the thing to break up. But W
did not seem to have problemsjust extruding from the fluid that was in the syringe the first time. If there
were any bubbles in there, I surely did not see any evidence of it. I don't know why there should have
been, come to think of it.
661
Question: When you start considering the low viscosity and low surface tension for certain classes of
optical materials, did you get any insight from what you have done here for how you might consider doing
something like that in micmgavity ?
Answer: Well, yes. The range of viscosity we chose was roughly around 10 kilo centistoke, if you like
that unit, but that is the way they are advertised up to 100,000 centistoke and that is roughly the range.
The 100,000 value is sort of the low end of the optical fibers that you would pull from silicon or silica.
The 10 k was dorm more of what you would expect of the fluoride systems as I understand it. I guess
the conclusion that I would have reached here, was that these were pretty fat fibers and they had to be
fat to last long enough to be measured. I am under the opinion of what I have seen so far, that the
gravity drainage is a very stabilizing effect in pulling fibers and probably you would run into very serious
trouble if you tried to do very thin fibers in microgravity. I am not sure there is an advantage to doing
that from what I have seen so far. I will have to look at that much more carefully before I make a blatant
statement but I guess what I am saying is, you can pull strands a lot easier on Earth than you can in
microgravity because of the gravity drainage effect. Rather than being something that hurts you it
seems to help you.
662
NUCLEATION OF CR [E-a01be685f4e205f1]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): t on
orbit. We documented deserts and we looked at dust storms coming over the Atlantic off the coast of
Africa. Any time you take over 4000 pictures on a flight it is a little difficult to find all the best ones to
show. But certainly, this gives you a little flavor of the view we had from orbit.
This flight ended over a year ago from now. Here we look at the data and we are looking at the
future of where we are going. We have been through some rather interesting months on the space
station and I do not need to tell you that. What it means is we are going through a reorganization. We
are going through a restructuring. But the intent is to continue on a space station track and to put a US
space station up there and to provide a platform for you to continue research. Interjected in all of this is
something that we have been working on for the last several months: an interim opportunity to work with
the Russians on the MIR. We will be flying the first cosmonaut on the Space Shuttle on STS-60, Sergei
Krikalev, and then we will be flying a second cosmonaut on STS-63, Vladimir Titov. We are going to be
putting an astronaut on the MIR in early '95. We will be docking the Shuttle to the MIR-1 in mid-95.
There is a plan for follow on flights. There are some opportunities to do some research in the biomedical
and life sciences area, and then the microgravity area. Bob Rhome will enlighten the microgravity
community and will be talking with some of you about what these potential opportunities are. The US
and Russians are currently engaged in negotiations to end somewhere around November 1 to determine
to what extent we will participate together in the International Space Station. Where we are going on that
is not easy to say. We have a lot of unknowns at this point, but I think what is important is for everybody
to remember the big picture; where the vision is. The research itself is important and we do not have
exploration without research, regardless of what may be the prevailing concepts; life support systems
require research. I have read articles about going to Mars and taking indigenous materials. Making
materials is going to require research especially because Mars has one-third Earth gravity. We need to
focus on the future and keep the path going. There are a lot of pictures in this museum and one of my
favorites is of Robert Goddard because he was a rather unique individual. When I was getting ready for
this mission, I know that a lot of people thought that maybe I was a little driven but I want you to know it
was hard not to be. I would go to bed at night and dream about the mission. I know a lot of you did too.
Only I would dream about day one or day five and how it ought to look. I saw a lot of problems in my
dreams and I was never embarrassed about that because I figured Robert Goddard never was. Y U go
O
out to the Goddard Space Flight Center and read the plaque out there and it says "Who is to say what
impossible, for it i the dreams of yesterday that are the hopes of today that are the realities of
s
tomorrow." I had an opportunity to work this mission starting in 1988 and I want to thank everyone of You
for helping my dreams come true.
938
INTERNATIONAL FLIGHT ACCELEROMETER DATA BASE
The International Flight Accelerometer Data Base is a collection O data on flight accelerometers and
f
acceleration measurement systems captured in an Excel spreadsheet. The custom software can be
used on IBM, IBM-compatible, and Macintosh personal computers. The data base currently contains
data on the following accelerometers and acceleration measurementsystems:
Accelerometer Name
Country
MASER Q-flex Accelerometers
Europe
General Active Micromotion Attenuator (GAMMA)
France
Micro AcceIerometer
France
MICROMEDY
France
SPOT3 On-ground Microvibrations Test
France
D-1-MEDEA-ACC
Germany
Microgravity Measurement System (MMS) [EURECA]
Germany
Microgravity Measurement Assembly (MMA) for Spacelab D-2
Germany
Microgravity Measuring Assembly (MMA)
G [E-1f129c9ecb7f6b59]
- Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA — recorded page 1 (physical PDF page unverified): Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA
Maria Thomsena,∗, Carlos Fernandez-Pelloa, Gary A. Ruffb and David L. Urbanb
aDepartment of Mechanical Engineering, University of California - Berkeley, Berkeley,
CA, 94720, USA
bNASA Glenn Research Center, 21000 Brookpark Rd., Cleveland, OH, 44135, USA
*
Corresponding Author (maria.thomsen@berkeley.edu; +1 (510) 701-8170)
Abstract
The flammability of combustible materials in a spacecraft is important for fire safety applications
because the conditions in spacecraft environments differ from those on earth. Experimental testing in
space is difficult and expensive. However, reducing buoyancy by decreasing ambient pressure is a
possible approach to simulate on-earth the burning behavior inside spacecraft environments. The
objective of this work is to determine that possibility by studying the effect of pressure on concurrent
flame spread, and by comparison with microgravity data, observe up to what point low-pressure can
be used to replicate flame spread characteristics observed in microgravity. Specifically, this work
studies the effect of pressure and microgravity on upward/concurrent flame spread over 10 mm thick
polymethyl methacrylate (PMMA) slabs. Experiments in normal gravity were conducted over
pressures ranging between 100 and 40 kPa and a forced flow velocity of 200 mm/s. Microgravity
experiments were conducted during NASA’s Spacecraft Fire Experiment (Saffire II), on board the
Cygnus spacecraft at 100 kPa with an air flow velocity of 200 mm/s. Results show that reductions of
pressure slow down the flame spread over the PMMA surface approaching that in microgravity. The
data is correlated in terms of a non-dimensional mixed convection analysis that describes the
convective heat transferred from the flame to the solid, and the primary mechanism controlling the
spread of the flame. The extrapolation of the correlation to low pressures predicts well the flame
spread rate obtained in microgravity in the Saffire II experiments. Similar results were obtained by
the authors with similar experiments with a thin composite cotton/fiberglass fabric (published
elsewhere). Both results suggest that reduced pressure can be used to approximately replicate flame
behavior of untested gravity conditions for the burning of thick and thin solids. This work could
provide guidance for potential ground-based testing for fire safety design in spacecraft and space
habitats.
Keywords: Flame spread rate, low pressure, environmental conditions, microgravity, PMMA
1
1. Introduction
Concurrent, or flow assisted, flame spread is particularly relevant in fire safety because it is generally
fast and consequently hazardous. It is for this reason that some material flammability tests use this
mode of flame spread to characterize the fire hazard of combustible materials. For example, NASA
relies on an upward flame spread test [1] to screen materials to be used in spacecraft cabins. A problem
with fire testing of spacecraft materials in normal gravity is that spacecraft fire conditions are very
different from those encountered on earth, particularly at the space exploration atmospheres (SEA) that
NASA is planning in using in future spacecraft. They include microgravity, low velocity flows, and
potentially low pressure (~60 kPa) and elevated oxygen concentration (~34%) [2]. The SEA
atmospheric conditions are designed to reduce preparation time for space walks, while keeping the
partial pressure of oxygen acceptable for human respiration [2,3]. However, because of flame-induced
buoyancy it is very difficult to reproduce on earth the environmental conditions of a spacecraft,
particularly the low velocity flows. The spacecraft ventilation system induces flows with velocities that
are of the order 100 mm/s to 200 mm/s, while the buoyant flow induced by a propagating flame have
velocities of the order of 300 mm/s to 600 mm/s. Thus, fire testing of materials to be used in spacecraft
requires either a red [E-4084124e9dc2a202]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): ng the acceleration. That was not easy. We found a system, finally, that is quite
smooth but that turned out to be one of the serious problems.
Question: What kind of rotational position accuracy do you achieve with the system ?
Answer: The accuracy in the positioning of 2 axis that is on the order of half a degree.
Question: How long does the flipping procedure fake ?
Answer: It takes about 1 second to flip over. We are trying to keep that period short. On the other
hand, it induces vibration and disturbance. That is a compromise between the requirements.
Question: About the performance data, you talked about it. How about some results? Before flight what
does your noise calibration look like ?
Answer: Yes. We tested the system. The task as I said in the beginning, was to measure
g within
very high level of noise. We did the following: We mounted our system on a plate and calibrated that
system by very sensitive quartz actuators and we found resolutions better than
g on ground. After
that calibration process, we mounted a shaker on to that plate, and the shaker excited the plate to about
5 g. Then we repeated our procedure by the actuators and we found the same signal, not affected by the
high vibration level of the sinusoidal vibration with 5g amplitude. We did this with a variable frequency
between 1 Hz and 50 Hz. That is a whole range of frequency we have qualified it for.
867
EURECA MICROGRAVITY ENVIRONMENT
- PRELIMINARY FLIGHT DATA
D. Eilers" and H. R. Stark+
'ERN0 Raumfahmechhnik, Bremen, Germany
+ ESA/ESTEC, Noordwijk, The Netherlands
ABSTRACT
EURECA, the European Retrievable Carrier, provides a new platform to perform microgravity
research in a low gravity orbital environment over extended duration of at least six months. The first
mission was launched in August 1992. After the free flying period, the EURECA spacecraft was
successfully retrieved by the Space Shuttle and landed on June 24, 1993. EURECA has been
designed for at least five launches and retrievals.
In order to comply with the stringent microgravity requirements, the EURECA system,
subsystem and payload performances shall maintain a controlled microgravity environment and shall
not exceed a limited acceleration response spectrum at the payload mechanical interfaces. Intensive
design, development and optimization activities were implemented and verified by simulations,
analyses and during an integrated system test on-ground. finally,
on-board acceleration
measurement system completed the information about the quality of the micro-g environment.
This paper summarizes the preliminary review of the residual accelerations as measured
during the first mission period of EURECA between 07.08.92 end the 1.10.92 in correlation with
the previous analysis and ground test results, as well as some later data.
The on-board Microgravity Measurement Subsystem 1MMS) detected the residual
accelerations after command from ESOC, the European Space Operations Center, in Darmstadt,
Germany. This review is namely based on a set of 906 acceleration measurements during the initial
.
period, with a duration of 3 167 minutes and in some cases up to 657.6 minutes.
The MMS data were transmitted from ESOC to the Microgravity User Support Centre
(MUSCl at DLR, K6ln-Porz, for processing and presentation. The preliminary evaluation provided
very interesting results. For instance, a dominant vibration frequency of 0.85 Hz is observed which
can correspond to a FEM-mode shape. A modulation frequency of 0.04 Hz could also be caused by
two aGacent mode shapes. Measurements over orbit periods show repetitive slight changes in the
vibration behavior beginning with and during each eclbse phase, etc.
The paper will present these findings and the conclusion that the desire design goal for the
microgravity quality on EURECA was met.
Joint Z + l Science Review for USMLl and USMF-1 with the Microgmvity Measurement GmUp, September
22-24, 1993, Huntsville, Alabama, USA.
869
INTRODUCTION
EURECA, as a larg [E-08c3327bddbeb4ae]
- Burning and Suppression of Solids–II  (BASS-II) Summary Report — recorded page 1 (physical PDF page unverified):  (1.2)
NASA/TM-20210011385 11
Using the ideal gas law, the free volume of the MSG V = 250,000 cc, ideal gas constant
R = 82.05 cc∙atm/gmol K, pressure P = 1 atm, the change of O2 percent volume, and temperature
T = 300 K, the gmol of O2 consumed is calculated as
2
2
O  consumed
O  vol%
1 250, 000
100gmol
82.05 300
PV
RT
∆ 
 
 = =
⋅
(1.3)
The gmol of fuel consumed is simply:
fuel
grams of fuel
gmol
molecular weight
=  (1.4)
Using the observed slope of 0.4582 O2 vol% per gram of fuel, and the molecular weight for PMMA
of 100 g/gmol for the majority of the data, we can use the above equations to solve for the effective
equivalence ratio for the tests: Φglobal = 1.3, which is fuel rich. So, in general, the flames were under-
ventilated and did not burn all of the vaporized fuel. Some fuel ended up as soot, some as CO, and some
as unburned hydrocarbons.
1.6 Overall Conclusions
As part of the Burning and Suppression of Solids—II (BASS–II) experiment, we conducted a number
of tests with different geometries, flow velocities, and initial O2 concentrations. The last variable was
enabled using gaseous N2 to dilute the working volume. To adequately characterize this dilution, we
developed a continuously stirred tank reactor model and verified it against sensor readings.
Sensor data from the tests showed that the O2 was burning nearly stoichiometrically to CO2, and that
CO levels appear to be a function of geometry and, in some cases, the flow velocity and geometry
combination. The CO to CO2 ratios for these fires are an order of magnitude higher than for efficient flue
gases, indicating that these flames are not efficient. The heat release was estimated for the tests using O2
consumption calorimetry. This showed that most of the tests released well below 100 W. In the one long
test that released close to 100 W, we sustained some damage to the downstream corner of the front
window, due to a leak that directed the heat from this energetic flame to that location during the
prolonged burn. Using the mass loss and O2 consumption data, the global equivalence ratio for the tests is
estimated to be 1.3 on average, which indicates the flames were burning fuel rich under the low-velocity
forced-flow conditions.
1.7 Acknowledgments
We want to acknowledge the invaluable assistance of the International Space Station crew in
obtaining these research results. Their meticulous operation and observations during the testing
contributed significantly to the quality and quantity of the results. Rick Mastracchio made an excellent
repair to the door that maintained the door seal integrity and interlock switch functionality throughout the
rest of the Burning and Suppression of Solids—II (BASS–II) operations. Alex Gerst and Reid Wiseman
repaired the video cable to provide the critical video overlay data only obtainable with that camera.
The crew was able to observe and describe some transient phenomena during ignition attempts and
near extinction that we could not observe on the ground, and they were able to adapt to new flow
variations such as blowoff extinctions, that proved to be very valuable data in outlining the U-shaped
flammability boundary.
NASA/TM-20210011385 12
This work could not have been done without the intense efforts of the BASS operations team (Jay
Owens, Chuck Bunnell, Tibor Lorik, and Carol Reynolds). We also want to acknowledge the ground
support teams at Glenn Research Center, Johnson Space Center, and Marshall Space Flight Center
(especially the Microgravity Science Glovebox team) that supported the BASS–II operations and assisted
in the anomaly resolutions.
1.8 References
1. Olson, S.L., et al.: Burning and Suppression of Solids—II Fire Safety Investigation for the
Microgravity Science Glovebox. Presented at the 29th Annual Meeting of the American Society for
Gravitational and Space Research (ASGSR) and the 5th International Symposium on Physical
Sciences in Space (ISPS), Orlando, FL, 2013.
https://www.researchgate.net/publication/ [E-5411d05d2ffb4e6a]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — recorded page 1 (physical PDF page unverified): f either exists. Observations of experimental spot ignition
characteristics and of the second transition over a thermally thin paper were made to
determine the effects of external flow velocity1. Both transitions have been studied
theoretically to determine the effects of the confinement by a relatively small test
chamber2, of the ignition configuration (ignition across the sample width vs spot
ignition)3, and of the external flow velocity4 on the two transitions over a thermally thin
paper.
This study is currently extending to two new areas; one is to include a
thermoplastic sample such poly(methymethacrylate), PMMA, and the other is to
determine the effects of sample thickness on the transitions. The recent results of these
new studies on the first transition are briefly reported.
Ignition and First Transition over PMMA
Ignition of a PMMA sheet (14 cm long x 10 cm width) was initiated at its middle
by a CO2 laser having a total power of about 28 W at the sample surface. The sheet was
mounted in the middle of the test chamber and exposed to a slow external flow of up to
10 cm/s. Therefore, subsequent flame spread from the localized ignition could occur
simultaneously upstream and downstream. There are two flames, one on the irradiated
surface and the other on the backside surface. Two different sheet thickness of 0.2 mm
and 0.4 mm were used. The experiment was conducted in the 10 s drop tower at the Japan
Microgravity Center, JAMIC. Ignition of the PMMA sample was observed shortly after
the start of the laser irradiation on the irradiated surface but subsequent ignition of the
backside surface (non-irradiated side) was significantly delayed. The delay increases with
the thicker sample and lower oxygen concentration as shown in Figure 1. Although the
number of the experiments is rather limited, the results show that the backside ignition
occurs only after the termination of laser irradiation in 21 % oxygen concentration. The
NASA/CP—2003-212376/REV1
125
duration of the laser irradiation could have
significant effects on the backside ignition.
This was demonstrated in the case of the
tests with external velocity of 5 cm/s in 21
% oxygen concentration with two different
irradiation times. A 6 s duration did not
ignite the backside within the available test
time of 10 s while a 3 s duration did ignite
the backside within 1 s after the termination
of irradiation. The behavior of flame during
the first transition to backside ignition and
subsequent anchored flame is shown in
Figure 2. It is curious that it takes several
seconds to ignite the backside in 21 % O2
concentration, even though there is an open
hole through the sample by the laser
irradiation shortly after the onset of the
front side ignition. After the laser
termination, the flame becomes very small
and moves close to the sample surface and
the open hole. Then, backside ignition
Figure 1. Effects of sample thickness on
ignition delay time of PMMA in
microgravity. (F-frontside/B-backside)-flow
velocity(cm/s)-O2 concentration.
Figure 2. Selected edge view video images of flame
behavior over 0.2mm thick PMMA sheet in 21 % O2 at
10 cm/s flow from right to left. Laser irradiation normal
to the sample surface from top. (a) 1.13s, (b) 3.16s, (c)
4.01s, and (d) 7.02s.
NASA/CP—2003-212376/REV1
126
occurs.
In 35 % O2 concentration, the
flame is brighter than that in 21
% O2 concentration and
backside ignition occurs before
the termination of laser
irradiation.
Similar
flame
behavior is also observed with
paper samples in microgravity.
In normal gravity, delayed
backside ignition was observed
with the PMMA samples in air
under the ceiling configuration
(upward
laser
irradiation
normal to a downward facing
sample surface). This curious
behavior of flame during the
first transition will be further
studied.
Our
numerical
calculation will be used to
understand why such long
delay occurs for the backside
ignition.
Ignition behavior of the PMMA sheet by a CO2 laser in zero gravity and al [E-9dc66a6421d1ebc7]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Approach; https://ntrs.nasa.gov/citations/20160000593 [E-context-5227141f2aaa7feb2e37]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II terrestrial reference tests; https://ntrs.nasa.gov/citations/20170008805 [E-context-a79df97c23d629116824]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II silicone results; https://ntrs.nasa.gov/citations/20170008805 [E-context-d86d030e275ce04b8b82]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-80d7fc00aae08504c315]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Material Ignition and Suppression Test; https://ntrs.nasa.gov/citations/20160000593 [E-context-87d3a70a788ae398fe4a]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-e6623c40985279bec3b2]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-3b27486ede2bf8151a2f]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, PMMA rod comparison; https://ntrs.nasa.gov/citations/20160000593 [E-context-d0e9f6c262d92e57e3bd]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-13fb7f02cdca2f8a]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — ntrs-20040053504, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20040053504 [E-dc10a634dcb57b01]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-a01be685f4e205f1]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-1f129c9ecb7f6b59]
- Buoyancy Effects on Concurrent Flame Spread Over Thick PMMA — ntrs-20200000557, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20200000557 [E-4084124e9dc2a202]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-08c3327bddbeb4ae]
- Burning and Suppression of Solids–II  (BASS-II) Summary Report — ntrs-20210011385, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20210011385 [E-5411d05d2ffb4e6a]
- Seventh International Workshop on Microgravity Combustion and Chemically Reacting Systems — ntrs-20040053504, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20040053504 [E-9dc66a6421d1ebc7]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-d1e50788b120206316a0]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-90f697823c2ba1b2ea82]



## What do the available investigations report under normal gravity?

QueryIntentV2 constraints: `[{"relation": "hasGravityCondition", "entity_id": "normal-gravity"}]`; requested classes: `['ReportedObservation', 'Intervention', 'NASAConclusion']`. Effective gravity policy: `{'enabled': True, 'explicit_values': ['normal-gravity'], 'comparative': False, 'default_preference': [], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['context:bass-ground-rod-observation', 'context:silicone-ground-observation']. RELATED: []. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.

## Applicable scientific context

- gravity: normal-gravity; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- oxygen: 21%; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd].
- gravity: normal-gravity; applies to context:silicone-ground-observation. The group statement and verified membership establish applicability [E-context-a79df97c23d629116824].
- material: context:silicone-material; applies to context:silicone-ground-observation. The group statement and verified membership establish applicability [E-context-a79df97c23d629116824].

## Direct evidence

- context:bass-ground-rod-observation [E-context-5227141f2aaa7feb2e37, E-context-87d3a70a788ae398fe4a, E-context-d0e9f6c262d92e57e3bd]
  Matches: ['hasGravityCondition=normal-gravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasGravityCondition: MATCH; requested: normal-gravity; actual: ['normal-gravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:silicone-ground-observation [E-context-a79df97c23d629116824]
  Matches: ['hasGravityCondition=normal-gravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasGravityCondition: MATCH; requested: normal-gravity; actual: ['normal-gravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Reported observations

- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
  Statement applicability — hasGravityCondition: MATCH; requested: normal-gravity; established: ['normal-gravity'].
  Topical statement selection does not establish every requested experimental condition
- In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.

In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn. [E-context-a79df97c23d629116824]
  Statement applicability — hasGravityCondition: MATCH; requested: normal-gravity; established: ['normal-gravity'].
  Topical statement selection does not establish every requested experimental condition

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Results of Large-Scale Spacecraft Flammability Tests — Summary and Conclusions: Flammability of silicone in microgravity appears to be reduced compared to normal gravity, at least for the flow speeds tested. [E-context-320a94a6feadb020fea3]
- Definition of experiments to investigate fire suppressants in microgravity — recorded page 1 (physical PDF page unverified): re.
tion 2.10.
Literature
information
literature.
reduced-gravity
trial)
agents.
REVIEW OF SUPPRESSION
This section
The specific
sections
in the project
2.0.
in space.
can be used to deliver
of various
references
provides
of plausible
technologies
into three
with separate
flight apparatus
representative
after which
on fire suppression
of the
(terres-
at the end of Section
2.0,
is
TABLE2.1.
CRITICALQUESTIONS
ONFIRE SUPPRESSION SPACE
IN
No.
Que_ons
1
Is technical information
available
2
Based on the phase, amount,
atmospheres to be expected
have a reasonable
with which
and configuration
on manned
probability
to evaluate
potential
of flammable
spaceflights,
spacecraft fire suppressants?
materials and the specifications
of the oxidizing
what is the nature of those fire situations, or scenarios,
that
of occurrence?
3
How
and to what extent does low gravity alter the physicochemical
4
How
and to what extent
do variables
characteristics of normal-gravity
combustion?
other than gravity influence the effectiveness of normal-gravity
fire
suppressants?
5
What
candidate
spacecraft, fire suppressants have been identified and recommended,
6
Have the alterations
to combustion
caused by reduced-gravity
effects been adequately
criteria for and analysis of spacecraft fire suppressants and atmosphere-inerting
consequences of this omission on the selection?
7
Based on the information available and its application,
recommended with confidence?
an annotated
Question
bibliography
and discuss
important
papers
can an effective, interim, spacecraft
of the documents
and reports
fire suppression
background
selectively
cited,
into the selection
fire suppressant
constituting
used here.
Lewis Research
Center,
To date,
been prevention
mable material
spacecraft
Microgravity
January
be
a response
to
Combustion
approach
and controlling
cannot
of onboard
spacecraft,
completely
flammable
of this
find-
of the
report.
No. 2)
fire safety
the amount of onboard
has
flam-
sources (2s). Obviously,
on protection
materials
such as the Space
and
held at the NASA
proceedings
(question
ignition
provided
the preliminary
by NASA to spacecraft
potential
depend
documents
Workshop,
by limiting
fire safety
will be summarized
the author reviewed
Fire Scenarios
(design to preclude)
tical for advanced
study, which
at the time of writing
the principal
The avoidance
of spacecraft
1989, but the published
Spacecraft
fire safety
the topic
for this
In addition,
were not available
2.3.
cover
in particular. (zs-ze,28,2e)hese
T
material
ings of the International
tion.
factored
gases, and if not, what were the
No. 1.
Several
workshop
and why?
by fire preven-
and combustion
Station
is imprac-
Freedom (2s,2e),
because
4
of the
complex,
and operations
permanent
planned.
operations
There are also serious
flammability
standards
for space
for waivered
flammable
articles.
ity of fire aboard
Freedom,
of an unwanted
fire
of the variety
flaming--could
and cannot
fire scenario
material
nents (7,14,15,18,25,29). secondary
A
explosion
threat
from either
the possibil-
procedures,
it is
smoldering
to
Freedom.
technical
literature
the smoldering
of a most
readily
control
is that a
of deep-seated
of electrical
less likely combustion
or the environmental
and storage
to zero (15c,18) Because
.
of the overheating
and much
of
is that the risk
of combustion--from
begins with
is from the evolution
smoldering
atmosphere,
be reduced
Station
as the result
on the definition
regarding
and experimental
the Space
experiments
of controls
the situation
from the review of available
spacecraft
questions
its Earth-like
materials
occur aboard
solid flammable
Hence,
all types and classes
A consensus
plausible
is finite,
of onboard
and on the adequacy
with
of necessary
likely that almost
and the variety
compo-
(flaming)
ignitible
gas,
and life support
and
H2,
system
(ECLSS).
Effect of
2.4.
The reduced-gravity
icochemistry
affecting
ject
mass and energy
of low gravity
the gravity
merely
on the two modes
compilation,
ment, and proce [E-f9c9d6f3bd3183e2]
- The Second International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): d
Optics.
7. Samson, R.1., Mulholland, G.W. and Gentry, 1.W., "Structural Analysis of Soot Agglomerates,"
Langmuir, 3, 272 (1987).
8. Dobbins, R.A. and Megaridis, C.M., "Morphology of Flame-Generated Soot as Determined by
Thermophoretic sampling," Langmuir, 3, 245 (1987).
9. Megaridis, C.M., "Thermophoretic Sampling and Soot Aerosol Dynamics of an Ethene Diffusion
Flame," Ph.D. Dissertation, Brown University (1987); also available as NBS report NBGCR-87-532.
10. Megaridis, C.M. and Dobbins, R.A., "Morphological Description of Hame-Generated Materials,"
Combustion Science and Technology, 71 , 95 (1990).
11. Kaylii, U. O. and Faeth, G.M., "Structure of Overfire Soot in Buoyant Turbulent Diffusion Flames
at Long Residence Times," Combustion and Flame, 89, 140 (1992).
12. Lekan, J. et al, "Constraints and Capabilities of Drop Tower and Aircraft Facilities," Proceedings of
the Second International Microgravity Combustion Worlcshop, 1992.
13. Meakin, P., Donn, B., and Mulholland, G.W., "Collisions between Point Masses and Fractal
Aggregates," Langmuir,S, 510 (1989).
144
Light Source
Source Aperture
.,------n..
Paraboloid Axis
_ _____ --.J{..... __ _
Condenser Lens ____
/
'\
Collimating Mirror
Edge
or
Rainbow
Filler
Camera
Figure 1
Typical Schlieren Optical System
Flow
Nozzle
----------------------~~
Thennophoreti
Probes
Figure 2
Therrnophoretic Soot Sampling Geometry
145
Ethylene 1.00 cc/... c
"'LeroG"
13.00
"
12.00
11.00
10.00
aJ
11.00
11.00
7.00
"
8.00
a.oo
4.0R.00
"
"
"
4.00
0.00
1n(Lm.u / dp)
11.00
Figure 3
Analysis of Ethylene Aggregates
Collimating
Lens
Microscope Objective
He-Ne
usa
Figure 4
Imaging Absorption Geometry
146
7.00
- _
. _-
- - - - --
- -
-
-
- - - - --
- - - - - - - -_ ._- _. .._ --
- ---- -
CO l\1MENTS
Question (Dr. Michael Winter, UTRC): What degree of temperature accuracy is available in the liquid- and
gas-phase measurement using the rainbow schlieren technique?
Answer: Accuracy in using the rainbow schlieren technique for either gas or liquid phase temperature
measurements depends on several quantities. First, the path length in which the refractive index changes
must be known to a high degree of accuracy. This is much easier to determine for liquids with fixed
boundaries or general axisymmetric distributions. In addition, the sensitivity of the system increases with the
focal length of the dccollimating lens. Finally, the quantity calculated is not temperature, but the refractive
index distribution. Therefore, knowledge of the constituent substances and the dependence of their index on
temperature is required before an accurate determination of the temperature can be made.
The foregoing begs the initial question (i.e., what temperature accuracies are available). We have measured
liquid-phase temperatures with a full-field difference of 1 K and a resolution within that field of 0.2 K. While
we have reconstructed refractive index profiles for gas-phase distributio ns, we have not yet performed
te mperature calculations, but expect to do roughly an order of magnitude worse.
Question (A. Gomez, Yale Uni\'ersity): Thermophoretic sampling used to capture aggregates as large as 12
mm may suffer from some biasing with respect to particle size, since you operate in the continuous regimes
(Kn approximately 10-2 to 10- 1). On Ihe other hand in the free-molecular regime (Kn greater than 1) , which
is typical of n-gravity names, there is no size-dependent effect on sampling. Could you comment on this
complication?
Answer: Thermoshoretic sampling of soot is a well-established technique for the study of soot produced in
varying names. 1- These studies were performed under normal gravity conditions. This question is directed
specifica lly toward sample biasing due to operation in the continuum regime for large aggregates present in
reduced gravity. A recent paper by Rosner, Mackowski and G arcia- Ybarra-l has shown that even in this
extreme, the maximum sa mpling bias will be at most approximately 20 percent. Therefore, t [E-fce4222c581f0db3]
- Sixth International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): inate just downstream of the premixed
branches.
ACKNOWLEDGMENTS
This work is currently supported by NASA Glenn Center for Microgravity Combustion Science.
REFERENCES
1.
2.
3.
4.
Chen, J.-Y. and Echekki, T., Numerical Study of Buoyancy Effects on the Structure and Propagation of Triple Flames,
to appear, Combust. Theory Modelling, 2001.
Chen, J.-Y. and Echekki, T., Proc. 5th Int. Microgravity Combustion Workshop, NASA/CP report 1999-208917 (1999).
Poinsot, T. and Lele, S., J. Comput. Physics, 101: 104-129 (1992).
Ruetsch, G.R., Vervisch, L. and Liñàn, A., Phys. Fluids 7(6): 1447-1454 (1995).
NASA/CP—2001-210826
351
NASA/CP—2001-210826
352
ESA - INSERT FOR NASA´S CIR:
ENVIRONMENT FOR COMBUSTION EXPERIMENTS UNDER
ELEVATED TEMPERATURE AND PRESSURE
Eigenbrod, Ch.*, König, J.*, Rath, H.J.*, Kufner, E.**
Center of Applied Space Technology and Microgravity, ZARM; Am Fallturm,
D-28359 Bremen, Germany, eigen@zarm.uni-bremen.de
** ESA/ESTEC, Noordwijk, The Netherlands, Ewald.Kufner@esa.int
Abstract
Within the course of DLR´s DROP-COS (Development and Research Program on PollutantReduced Combustion Systems) project and ESA´s CPS-MAP (Combustion Properties of
Partially Premixed Spray Systems – Microgravity Applications Promotion Program) project, a
drop tower facility for droplet autoignition investigations at elevated pressure and temperature
was developed. This facility shall be adopted as an insert for NASA´s CIR in order to enable
combustion experiments at elevated pressure and temperature. This insert can complement
existing (or planned) inserts delivering a furnace equipped diagnostible combustion chamber
applicable to droplet- and particles investigations as well as for gaseous combustion to take place
at various ambient temperature conditions. An ongoing phase A study shall verify the feasibility
of the implementation into the CIR as well as reflect on the optimal flexibility in order to serve
different users demands.
Project description
Investigations of the selfignition process of fuel froplets and sprays at elevated temperature and
pressure at sub- and supercritical conditions are ongoing in Europe since many years. The
technical background is to aim for a fundamental understanding of the physical and chemical
processes finally leading to the autoignition of fuel sprays. This is required to enable the
development of numerical simulations of the process predicting the behaviour of reactors that
either need controled autoignition for a proper operation (diesel-engines) or have to avoid
unwanted autoignition (internal combustion engines, gas-turbines). As the LPP-concept (leanprevaporized-premixed) has been proven as the most promising method to lower local
combustion temperatures below the onset temperature of thermal NOx formation, it might be
possible to apply this method also to aero-engines supplemeting the RQL process actually be in
use. Knowledge in detail is therefore needed the more as aero-engines are difficult to design
flashback-safe on one hand and rising inlet temperatures and pressures limit the time available
for vaporization and turbulent mixing on the other hand.
Microgravity environment is needed as the physical and chemical processes must be basically
examined without the masking effects of natural convection of a flow field. In normal gravity
more dense fuel vapour drops off the droplet and exothermal precursor reactions reduce the local
density in the viscinity of a droplet. As a specific advantage of this issue, the micron-sized
droplets of a technical spray do not strongly interact with the turbulent flow field and natural
convection plays a minor role during the milliseconds lifetime of such droplets. Therefore, the
transformation of results from microgravity experiments on comparably large droplets (easy to
handle, easy to diagnost) to technical applications has to bridge only small gaps.
NASA/CP—2001-210826
353
Experiments in high pressure and high temperature have been performed utilizing the Bremen
drop [E-cf52002d9d2fe8f4]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): data from Runs 1.O and 1.l; off); Thermocouples 1 to 4.
(Fan
300
200
100
’
0
0
2
4
6
-
20
Time, Minutes
Figure 3 Temperature data from Runs 2.0 and 2.1 (Fan on); Thermocouples 1 to 4.
625
0
400
El00
Q)
I
-
n
" 0 1
Figure 4 Igniter Temperature Comparison.
626
2 3 4 5 6 7 8
Time, Minutes
Figure 5 Foam Samples, from Runs 1.O (Left) and 2.0 (Right), Fan end at base of figure. Samples are 8
cm long.
627
.. .
Figure 6 Foam Samples, from Runs 1.1 (Top) and 2.1 (Bottom), Fan end at left, Gravity Vector down.
Samples are 8 cm long.
628
Discussion
(Speaker: Carlos Femandez-Pello, University of California, Berkeley, California)
Question: When you see a lot of CO produced in a reaction that under other conditions does not
produce a lot of CO, my naive view is that somehow I have limited the amount of oxygen getting to this
combustionp c e s s , and that is why I don't go to completion in that reaction. Is that consistent with your
interpretation of these results?
Answer: Yes. Basically I think what happens is the supply of oxidizer is by diffusion and what we have in
microgravity is we have a higher temperature, with higher pyrolysis of the fuel, and an attempt to react
more than in normal gravity. We are comparing normal and microgravity. In normal gravity the
convective flow cools the reaction and prevents this from occurring, but in microgravity there is not
enough oxidizer to oxidize the CO to C02. One thing that is a bit deceiving, also, is that this is a surface
reaction, so when we think of the oxidation process in the gas phase, that occurs at above 1000°C. Here,
in the experiment, the temperatures are of the order of 4OO0C, so the concepts that apply to the oxidation
process in flames do not apply here. But basically you are right.
629
WIRE INSULATION FLAMMABILITY EXPERIMENT: USML-1
1 YEAR POST MISSION SUMMARY
Paul S. Greenberg*, Kurt R. Sackstedef and Takashi Kashiwagi’
*NASA Lewis Research Center, Cleveland, OH
‘National Institute of Standards and Technology, Gaithersburg, MD.
ABSTRACT
Herein we report the results from the Wire lnsulation Flammability (WrF) Experiment performed in
the Glovebox Facilify on the USML-1 mission. This experiment explored various aspects of electrically
induced fire scenarios in a reduced gravity environment. Under quiescent microgravity conditions, heat
and mass transfer are dominated by diffusive and radiative transport; while in normal-gfavity buoyancyinduced convection offen dominates. Of considerable scientific and practical interest is the intermediate
situation of combustion occuning in the presence of imposed gas Mws, with lower characteristic
velocities than those induced by buoyancy in noma1 gravity. Two distinct cases naturally arise: flow
direction opposed to, or concurrent with, the flame spread dimction. Two tests of each kind were
conducted in the WIF experiment, providing the first controlled demonstration of flame spreading in forced
convection ever conducted in space.
Four test modules were flown. The wire insulation, 1.5 mm in diameter, was polyethylene,
extruded onto nichrome wire. Temperatures of the wh3 cores and insulation heated in quiescent and
flowing environments were measured. Video and still-camera images of the samples, burning in air
flowing at appximately 10 cm/sec, were recorded to obtain flame characteristics including spread rate,
structure and temperature. Flame spread rates in concurrent flow were approximately twice those in
opposed flow.
Several unexpected and unique micxogavity combustion phenomena were observed.
In
concurrent and opposed flow regimes, the spreading flames stabilized around a bead of molten insulation
material, within which bubble nucleation was observed. An ignition attempt without flow mated a
quiescent cloud of vaporized fuel which ignited dramatically yet failed to sustain normal flame spread.
Finally, all tests produced substantial soot agglomerates, patticularly the concurrent flow tests; and the
collected soot has a morphology very disti [E-c8f8ed9b6bd9012e]
- Organizing Questions for Reduced-Gravity Flammability — recorded page 1 (physical PDF page unverified): e
16.5
PMMA (Perspex)
tube
LOI
Polyurethane foam
LOI Apparatus
95
NASA/CP—2004-213205/VOL1
Fire in Microgravity
National Aeronautics and
Space Administration
John H. Glenn Research Center
5. How can the results of small-scale experiments be used to
determine the behavior of large-scale fires?
a. Extend results to conditions and geometries that haven’t
been tested
b. How will flames grow and spread in real situations?
622
NASA Std. 6001
Test 1
Other lab
Tests
Understanding
Microgravity Fire
Numerical
Models
Flight
Experiments
Large-Scale
µg Test?
NASA/CP—2004-213205/VOL1
Exploration Environments
National Aeronautics and
Space Administration
John H. Glenn Research Center
6. How do the flammability and ignitability of materials change in
high-O2 mole fraction, low-pressure, reduced gravity
environments?
• Exploration environments may have an enriched oxygen, low
pressure atmosphere.
623
• Skylab 70% oxygen, 5 psia
• Apollo 100 % oxygen, 5 psia
• EVA Shuttle/ISS 30% oxygen
• Test 1 is run at atmosphere of use, though data base is
smaller at higher oxygen concentrations.
NASA/CP—2004-213205/VOL1
Smoldering
National Aeronautics and
Space Administration
John H. Glenn Research Center
7. How does the propensity for non-flaming/smoldering
combustion of materials change in high-O2 mole fraction, lowpressure, reduced gravity environments?
624
• Smoldering not covered under
NASA Std. 6001, Test 1.
• One planned flight experiment:
Smoldering, Transition and
Flaming (STaF)
Polyurethane
Foam
(5 cm x 5 cm
x 125 cm long)
Smolder
Front
PI: Prof. Carlos Fernandez-Pello
Univ. of Cal. at Berkeley
Igniter
NASA/CP—2004-213205/VOL1
Ignition & Products
National Aeronautics and
Space Administration
John H. Glenn Research Center
8. What are the other credible ignition sources, other than electrical
overheating and electrical short circuits that will exist on exploration
vehicles? Do these sources increase or decrease the propensity for
ignition in reduced gravity?
625
•
•
•
•
Waste Storage
Solid Fuel Oxygen Generators
High pressure oxygen system
Laser use?
NASA/CP—2004-213205/VOL1
Your Input
National Aeronautics and
Space Administration
John H. Glenn Research Center
Questions:
Are these the right questions?
•
626
•
How would you change them?
•
Are there other questions that should be considered?
Concepts:
Reiteration of what we need to determine:
1.
What experiments must be conducted to best answer
these questions?
2.
Can some of the questions be answered using
existing/planned hardware or experimental concepts?
NASA/CP—2004-213205/VOL1
National Aeronautics and
Space Administration
John H. Glenn Research Center
Flow Enclosure Accommodating Novel
Investigations in Combustion of Solids
(FEANICS)
627
June 23, 2004
NASA/CP—2004-213205/VOL1
National Aeronautics and
Space Administration
John H. Glenn Research Center
Combustion Integrated Rack Overview
Environmental Control (ECS)
• Air Thermal Control
• Fire Detection & Suppression
• Water Thermal Control
• Gas Interfaces (GN2, VES, VRS)
Fuel/Oxidizer
Management
Assembly (FOMA)
International Standard
Payload Rack (ISPR)
Image
Processing and
Storage Unit (2)
(IPSU)
Rack Closure
Door
Combustion
Chamber
628
SAMS
RTS
Optics
Bench Slides
Passive Rack
Isolation
Subsystem
(PARIS)
Optics
Bench
FEANICS
Chamber Insert
Assembly
FOMA
Control
Unit
(FCU)
Input/Output
Processor
(IOP)
Science Diagnostics
• Color Camera
• Illumination Package
• Mid IR Camera
• Low Light Level (2 Units)
• High Bit Depth Multi-Spectral
• High Frame Rate/High Resolution
OR
Experiment Specific Diagnostics
PI
Avionics Box
Electrical Power
Control Unit (EPCU)
Laptop
Computer
NASA/CP—2004-213205/VOL1
FEANICS-1 Capabilities
National Aeronautics and
Space Administration
John H. Glenn Research Center
•
629
•
•
•
•
•
•
•
15 cm W x 12 cm H x 30 cm L flow tunnel test section
– Top surface of fuel flush with tunnel floor
– 0-25% and 4-96% O2 sensors at tunnel inlet and outlet
– 4 LEDs for illumination
– Gas phase thermocouple for gas inlet and outlet tempera [E-626767f8cbac8cd0]
- The Second International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): the KC-135 is ope rated out of JSc, the Marshall Space Flight Center
(MSFC) has the responSibility for coordinating and scheduling flights for experiments sponsored by the
MSAD of NASA Headquarters. LeRC personnel are availab le to assist investigators with the various
documentation and contacts (MSFC and JSc) necessary for meeting the requirements for KC-135 flights.
Also, LeRC-sponsored KC-135 experiments per JSC guidelines must be reviewed and approved by the
LeRC Airworthiness Review Panel. The hardware will also be reviewed by a J5C safety committee for
approval prior to flight. The "JSC Reduced Gravity Program User's Guide" provides complete details
of experiment design guidelines and requirements for personnel who will be flying on the KC-135.
50
Another aspect of facility utilization involves coord ina tion with NASA personnel. A NASA
researcher or scientist is assigned to be a contract technical representative to any LeRC-sponsored
investigation in the ground-based facilities. This individua l will have the responsibility to provide
the sponsored researcher with the necessary guidance regard ing facility utilization and also assist in
establishing an interface with operations personnel in the various facilities. The activities that wiJI
be coordinated with this individual include the following: arrangement of a pre-design meeting with
the appropriate operations and design engineers to discuss the investigation, objectives, measurements
required, hardware needs, design and procurement responsibilities and the like; maintenance of
communications with operations personnel during the design and build-up phase; assistance in the
preparation of a Test Request Document (directed to the appropriate operations engineer) w hich
formally defines experiment details and experiment milestones, etc. ; assistance in scheduling tests;
and consultation during the testing phase. LeRC mechanical and electronics technicians are available
during the testing phase for repairs or modifications that cannot be performed by the investigator. This
support may not always be available in a timely manner due to the many investigations that are
ongoing.
Experiment Hil rdwil re I I nves tigil tia ns
As stated earlier, the NASA ground-based facili ties have supported a wide range of investigations
over the past thirty years particularly in the fields of combustion and fluids. Table 4 represents a
sampling of a few of the recent experiment programs that have been carried out in the facilities. Many
of the investigations have utilized more than one faci li ty. A description of some of the hardware will
be presented to show what is feas ible. Of course these descriptions represent examples of capabilities.
Simpler or more complex systems have been or can be engineered depending on the needs of the
inves tiga tion.
The inventory of operational drop rigs at the Drop Tower has reached twenty-five with several more
in the build-up phase. One of those that will soon become available is an updated multipurpose, multiuser combustion rig that will address investigations including solid material flammability, gas-jet
diffusion flames, candle flames, and spacecraft fire safety. The test chamber for this rig will have an
internal volume of .027 m3 (.25 m 1. 0 ., .53 m length), a working pressure of 4.8 atmospheres, five
viewing windows, and several feedthro ughs and penetrations for mechanical and electrical hardware
connections. The data acquisition capabilities will incl ude accommodations for four thermocouples, one
pressure transducer, and movie and video systems. The rig will also have provisions for a laser light
sheet and a shock absorption plate system for the mounting of sensitive components.
Since there are fewer ex peri men t vehicles available at the Zero-Gravity Facility, more multipurpose
hardware exists, particularly for combustion research. There are three combustion experiment vehicles
available. They contain combustion chambers with the following  [E-0736c640fe2b2d83]
- The Second International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): uman comfon and
performance mainly depend on the absolute amount of oxygen in the attnosphere. Thus, it may be
possible to find a composition for spacecraft atmospheres that will not suppon combustion but will
suppon normal human activities indefinitely. However, available information concerning fire-safe
aunospheres - combustion properties at ~g, the performance and health of humans and other
biological systems, and potential impacts on spacecraft design and operation - are woefully
68
inadequate in view of the importance of this selection. Thus, fire-safe atmospheres appear to merit
a broad-based interdisciplinary research program due to their potential impact on future human
activities in space.
Current Priorities for Micromvity Combustion Research
An objective of this workshop is to identify priority areas within combustion science where
micro gravity-based investigations are needed. Based on the results of the First International
Microgravity Combustion Workshop, the Discipline Working Group (DWG) that advises NASA
in the area of micro gravity combustion science has set the following priorities: (1 ) turbulent
reacting flows; (2) heterogeneous combustion such as droplets, particles, slurries, solid fuels and
pools of liquid fuels; and (3) laminar homogeneous combustion phenomena such as ignition,
fiarneholding, t1ammability limits, flame instabilities, and diffusion flames. Prioritization also was
made with respect to applications, with spacecraft fire safety selected as the single most important
application area.
The current microgravity combustion science program only reflects these priorities with respect to
relevance to spacecraft fire safety, with the bulk of the work associated with heterogeneous
combustion. This status is summarized in T able 1. In this table , flight studies denote
investigations that are candidates for experimentation in space. Other studies either use groundbased IJ.g facilities, such as drop towers and aircraft flying parabolic trajectories, or are theoretical
studies. The relatively few studies of turbulent combustion is surprising in view of the current
high priority of this area. In contrast, seven flig ht studies and 18 total studies are related to
spacecraft fIre safety, implying a strong response to this priority area following the last NASA
Research Announcement (NRA) in 1989.
Table 1 Current Microgravity Combustion Science Program
Priority
J
3
Flight
Studies
Area
Turbulent Reacting Flows
Heterogeneous Combustion
Laminar Homogeneous Flames
1
7
2
Total
Studies
'"l
j
19
6
Goals for W orlcshop Discussions
As the microgravity combustion science program develops both the priorities and the focus of the
research program will change. Thus, an objective of the workshop is to highlight areas where
changes shoulq be encouraged. Some questions that might be addressed during the discussions
are as follows:
l.
Are the areas and priorities selected by the DWG appropriate?
2.
Are there new areas, e.g., combustion synthesis, metal combustion, etc., that merit emphasis
in the next NRA?
3.
What should be done to improve the content and balance of the flight and ground-based
programs. and of experimental and theoretical programs?
L_
69
4.
Should a major interdisciplinary research program on spacecraft fIre-safe atmospheres be
recommended and what should be the combustion component of any such program?
S.
Does the present program adequately address fundamental research issues relevant to
spacecraft fire safety?
Funding is competitive within the micrograviry combustion science program, and perhaps more
importantly , between this program and other research areas of interest to NASA and other
government agencies. Thus. an active high-quality rnicrogravity combustion science program is
required to assure continuing funding levels - much less increases. This workshop is one step in
developing such a program; therefore, lively and productive discussions here will be a valuable
service to the field of combustion.
 [E-129ba4f7d3063d67]
- Microgravity Smoldering Combustion on the USML-1 Space Shuttle Mission — recorded page 1 (physical PDF page unverified): Time, Minutes
Figure 2 Temperature data from Runs 1.O and 1.l; off); Thermocouples 1 to 4.
(Fan
300
200
100
’
0
0
2
4
6
-
20
Time, Minutes
Figure 3 Temperature data from Runs 2.0 and 2.1 (Fan on); Thermocouples 1 to 4.
625
0
400
El00
Q)
I
-
n
" 0 1
Figure 4 Igniter Temperature Comparison.
626
2 3 4 5 6 7 8
Time, Minutes
Figure 5 Foam Samples, from Runs 1.O (Left) and 2.0 (Right), Fan end at base of figure. Samples are 8
cm long.
627
.. .
Figure 6 Foam Samples, from Runs 1.1 (Top) and 2.1 (Bottom), Fan end at left, Gravity Vector down.
Samples are 8 cm long.
628
Discussion
(Speaker: Carlos Femandez-Pello, University of California, Berkeley, California)
Question: When you see a lot of CO produced in a reaction that under other conditions does not
produce a lot of CO, my naive view is that somehow I have limited the amount of oxygen getting to this
combustionp c e s s , and that is why I don't go to completion in that reaction. Is that consistent with your
interpretation of these results?
Answer: Yes. Basically I think what happens is the supply of oxidizer is by diffusion and what we have in
microgravity is we have a higher temperature, with higher pyrolysis of the fuel, and an attempt to react
more than in normal gravity. We are comparing normal and microgravity. In normal gravity the
convective flow cools the reaction and prevents this from occurring, but in microgravity there is not
enough oxidizer to oxidize the CO to C02. One thing that is a bit deceiving, also, is that this is a surface
reaction, so when we think of the oxidation process in the gas phase, that occurs at above 1000°C. Here,
in the experiment, the temperatures are of the order of 4OO0C, so the concepts that apply to the oxidation
process in flames do not apply here. But basically you are right.
629 [E-21e20799b88feef6]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Approach; https://ntrs.nasa.gov/citations/20160000593 [E-context-5227141f2aaa7feb2e37]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II terrestrial reference tests; https://ntrs.nasa.gov/citations/20170008805 [E-context-a79df97c23d629116824]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Summary and Conclusions; https://ntrs.nasa.gov/citations/20170008805 [E-context-320a94a6feadb020fea3]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Material Ignition and Suppression Test; https://ntrs.nasa.gov/citations/20160000593 [E-context-87d3a70a788ae398fe4a]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, PMMA rod comparison; https://ntrs.nasa.gov/citations/20160000593 [E-context-d0e9f6c262d92e57e3bd]
- Definition of experiments to investigate fire suppressants in microgravity — ntrs-19910005065, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19910005065 [E-f9c9d6f3bd3183e2]
- The Second International Microgravity Combustion Workshop — ntrs-19930010989, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19930010989 [E-fce4222c581f0db3]
- Sixth International Microgravity Combustion Workshop — ntrs-20010073993, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20010073993 [E-cf52002d9d2fe8f4]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-c8f8ed9b6bd9012e]
- Organizing Questions for Reduced-Gravity Flammability — ntrs-20040142368, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20040142368 [E-626767f8cbac8cd0]
- The Second International Microgravity Combustion Workshop — ntrs-19930010989, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19930010989 [E-0736c640fe2b2d83]
- The Second International Microgravity Combustion Workshop — ntrs-19930010989, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19930010989 [E-129ba4f7d3063d67]
- Microgravity Smoldering Combustion on the USML-1 Space Shuttle Mission — ntrs-20030075804, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075804 [E-21e20799b88feef6]



## Which conditions applied to the Saffire-I experiments?

QueryIntentV2 constraints: `[{"relation": "belongsToInvestigation", "entity_id": "psi-98"}]`; requested classes: `[]`. Effective gravity policy: `{'enabled': True, 'explicit_values': [], 'comparative': False, 'default_preference': ['microgravity'], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['psi-98-S1', 'psi-98-S2']. RELATED: []. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.
Research preference: microgravity. Experimental conditions are established by the cited sources.

## Applicable scientific context

- gravity: microgravity; applies to psi-98-S1, psi-98-S2. The group statement and verified membership establish applicability [E-context-0bacb5f04c6c34659dcc, E-context-7973df3a5b7f8b12b64d, E-psi-98-table-S1].

## Direct evidence

- psi-98-S1 [E-psi-98-table-S1]
  Matches: ['belongsToInvestigation=psi-98']; differs: []; unknown: []; invalid: [].
  belongsToInvestigation: MATCH; requested: psi-98; actual: ['psi-98'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- psi-98-S2 [E-psi-98-table-S2]
  Matches: ['belongsToInvestigation=psi-98']; differs: []; unknown: []; invalid: [].
  belongsToInvestigation: MATCH; requested: psi-98; actual: ['psi-98'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Results of Large-Scale Spacecraft Flammability Tests — Concurrent and opposed-flow comparison: Left: Flame base and pyrolysis position for concurrent and opposed-flow test in Saffire-1. Air flow speed was 20 cm/s.

Right: Spread rate summary for cotton/fiberglass fabric burning in microgravity. Concurrent flames are shown to the
left of the origin, and opposed to the right. [E-context-0bacb5f04c6c34659dcc]
- Results of Large-Scale Spacecraft Flammability Tests — Saffire-I Description and SIBAL results: Saffire-I Description
Large sample (40.6 cm x 94 cm)
Flow speed of 20 cm/s
Initial oxygen concentration 21.7% (ISS reading)

• Only concurrent-flow test was planned; opposed-flow test was a contingency.
• Everything performed nominally for the first test which was allotted 420 s before
the air flow turned off.
• About 90% of the fuel burned in the first test leaving 10% unburned, allowing a
meaningful opposed-flow test to be completed.

14

Fuel characteristics (“SIBAL” fabric)
75% cotton, 25% fiberglass blend
Simple weave pattern (60 x 40 threads per inch)
Cotton and fiberglass fibers intermingled
Overall area density: 18 mg/cm2
Fuel sizes (W x L): 40.6 x 94 cm and 5 x 29 cm

SIBAL Fabric Results
• 40.6-cm-wide concurrent-flow test: flame ignited across the bottom of the fuel
‒ At ignition, the flame was mostly bright yellow and relatively vigorous but it soon developed a blue base and
a pattern of orange radiation coming from incandescent soot
‒ Initially the flame length fluctuated at about 1.4 Hz before finally becoming more stable at about 90 s
‒ After the flame had passed, exothermic surface smolder spots burning some of the leftover fuel were visible
‒ The flame burned the entire allotted test time of about 7 min. at which point the air flow was shut off and
the flame immediately extinguished
• 40.6-cm-wide opposed-flow test: flame ignited across the top of the fuel
‒ There was a small but sufficient amount of fuel remaining after the concurrent-flow test of the first
experiment to permit an opposed-flow test
‒ Only about 10% of the fuel remained after the concurrent test, but that was enough to make conclusions
about the opposed-flow flame spread and development
• 5-cm-wide concurrent-flow tests: flame ignited across the bottom of the fuel
‒ Two flow speeds tested; 20 and 25 cm/s [E-context-7973df3a5b7f8b12b64d]
- Operation and Development Status of the Spacecraft Fire Experiments (Saffire) — recorded page 1 (physical PDF page unverified): priority placed
on material flammability in exploration atmospheres – e.g. in ambient conditions having oxygen mole fractions up
to 0.34 and pressures of 8.2 psia. These conditions bound those considered for exploration missions. While elevated
oxygen and reduced pressure conditions are generally considered for planetary or asteroid operations where frequent
extravehicular activities (EVA) are required, the Cygnus environment provides the unique opportunity to explore
these conditions at relevant scales and obtain data that can anchor computational models that will be applied during
analysis of fire scenarios.
7
International Conference on Environmental Systems
Table 2. Spacecraft Fire Safety Demonstration Experiment Objectives
Area
Objective
Quantify growth and end state of realistic fires
Fire behavior/modeling: in spacecraft and their influence on vehicle
habitability
Comment
Saffire-I, II,
III
Saffire-IV,
V, VI
X
X
Require to validate computational
models
Ground
Flame behavior in complex geometries
Flame behavior for planar and complex
geometries in exploration atmospheres
Elevated O2, lower P; compare with
Saffire-I, II, III; supplement small-scale
tests in CIR
X
Continues Saffire-I and III investigations
Demonstrate performance of prototype Orion
and ISS CPM
Demonstration of prototype flight
hardware
X
X
Obtain data to validate transport and detection
Required for model development
models
Post-fire monitoring
X
Measure flame behavior over large-scale
planar surfaces
Fire growth/dynamics
More realistic configurations than SaffireI, II, and III
X
X
X
X
Demonstrate fire detection with multi-moment
sensors
Demonstrate capability to reject
nuisance alarms
X
Evaluate performance of hybrid fire detection
(smoke and gaseous products)
Combustion product detection by
prototype combustion product monitor
X
Quantify rate of decay of gas species after a
spacecraft fire
Required for model development
X
X
Post-fire cleanup
Quantify atmosphere cleanup rate with
prototype smoke-eater
Demo of prototype flight hardware
X
X
Fire Suppression
Performance of low-momentum water mist
suppression
Effectiveness of fire ports using water
mist fire suppression
Fire Detection
Post-fire monitoring
X
For fire detection, the size of smoke particulate produced in low-gravity has been investigated by the Smoke
Aerosol Measurement Experiment (SAME)7,8. Transport models of smoke and combustion products have been
developed based on these results but the models themselves have not been validated. The Saffire-IV-VI experiments
in a Cygnus vehicle provide the unique opportunity to obtain this data. Similarly, the transport and detection of
gaseous combustion products, especially acid gases like hydrogen fluoride (HF) and hydrogen chloride (HCl) that
have a propensity to attach to smoke particulate and other surfaces must be quantified to define fire response
protocol. Additionally, the demonstration of a post-fire monitoring technology for these chemical species will
significantly advance the technology readiness level (TRL) of this instrument and bring it closer to implementation
both on ISS, Orion, and future exploration vehicles.
Obtaining data on the ability of advanced sorbents to remove carbon monoxide (CO) from the atmosphere in a
spacecraft environment will aid spacecraft environmental control and life support (ECLS) designers to develop
systems that can rapidly clean-up the cabin atmosphere following a fire event. The Cygnus vehicle provides a
unique environment to demonstrate this technology and provide data essential for the design of clean-up systems for
exploration vehicles and habitats.
The ground tests in post fire monitoring and cleanup indicated in Table 2 are planned for a Spacecraft Flow
Simulator Facility being constructed at NASA-GRC. This facility will be similar to the geometric and volumetric
configuration of the Cygnus vehicle with the ability to include advanced diagnostics to characterize particulate and
gaseous combustion product tra [E-1ac66b2fe73347e1]
- Determining Flame Temperature By Broadband Two Color Pyrometry in A Flame Spreading Over A Thin Solid in Microgravity — recorded page 1 (physical PDF page unverified): Determining flame temperature by broadband two color
pyrometry in a flame spreading over a thin solid in
microgravity
Maria Thomsena,∗, Juan Jose Cruzb, Felipe Escuderob, Andres Fuentesb,
Carlos Fernandez-Pelloc, Michael Gollnerc, David L. Urband, Gary A. Ruffd
aFaculty of Engineering and Sciences, Universidad Adolfo Ibáñez, Santiago, Chile
bDepartamento de Industrias, Universidad Técnica Federico Santa Marı́a, Av. España 1680, Valparaı́so, Chile
cDepartment of Mechanical Engineering, University of California Berkeley, Berkeley, CA, USA
dNASA Glenn Research Center, 21000 Brookpark Rd., Cleveland, OH, USA
Abstract
Fire spread inside a spacecraft is a constant concern in space travel. Understanding how the fire grows and
spreads, and how it can potentially be extinguished is critical for planning future missions. The conditions inside
a spacecraft can greatly vary from those encountered on earth, including microgravity, low velocity flows, reduced
ambient pressure and high oxygen, and thus affecting the combustion processes. In microgravity, the contributions
of thermal radiation from gaseous species and soot can play a critical role in the spread of a flame and the problem
has not been fully understood yet. The overall objective of this work is to address this by studying the soot
temperature of microgravity flames spreading over a thin solid in microgravity. The experiments presented here
were performed as part of the NASA project Saffire IV, conducted in orbit on board the Cygnus resupply vehicle
before it re-entered the Earth’s atmosphere. The fuel considered is a thin fabric made of cotton and fiberglass
(Sibal) exposed to a forced flow of 20 cm/s in a concurrent flow configuration. Reconstruction of the flame
temperature fields is extracted from two color broadband emission pyrometry (B2CP) as the flame propagates
over the solid fuel. A methodology, relevant assumptions and its applicability to other microgravity experiments
are discussed here. The data obtained shows that the technique provides an acceptable average temperature around
∼ 1300 K, which remains relatively constant during the spread with an error value smaller than 117 K. The data
presented in this work provides a methodology that could be applied to other microgravity experiments to be
performed by NASA. It is expected that the results will provide insight for what is to be expected in different
conditions relevant for fire safety in future space facilities.
Keywords: Broadband pyrometry; Soot temperature; Boundary layer diffusion flame; Concurrent flame spread; Sibal material.
Corresponding author: ∗ maria.thomsen@uai.cl
1
1. Introduction
Understanding the behavior, spread and growth of
a fire inside a spacecraft is essential to develop meth-
ods to prevent and respond to the occurrence of fire
accidents that could endanger the success of a mis-
sion and the safety of the crew. Currently, materi-
als used inside spacecraft cabins or the International
Space Station (ISS) are rigorously screened to charac-
terize their fire hazard and determine how they would
behave in case of a fire [1, 2]. Although ideally, the
testing of materials would be done under the actual
conditions of the cabin where it is intended to be used,
this is sometimes challenging given that testing in a
space-based facility is very expensive and very lim-
ited in available space and opportunities.
Aiming to expand the knowledge of fire spread and
growth, and material flammability in spacecraft en-
vironments, NASA embarked on a research project,
the Spacecraft Fire Experiment (Saffire) [3], that aims
to better understand material flammability and fire
growth and spread. The Saffire experiments are a se-
ries of unique and novel large-scale spacecraft exper-
iments performed on board the Cygnus cargo space-
craft, after the vehicle has completed its primary mis-
sion to the ISS, and before its planned destructive
reentry through Earth’s atmosphere. Using this ve-
hicle to perform large- [E-18c496f0304c63ce]
- Spacecraft Fire Safety Demonstration — recorded page 1 (physical PDF page unverified): enced by natural
convection
•
•
Normal gravity flames induce a natural convective flow that transports oxygen to the
flame but also removes heat
Forced convection in low-g transports oxygen to the flame but rate of heat removal is
reduced
% Oxygen
0g quiescent limit
Flammable
Fundamental limit
Not Flammable
1-g buoyant air
speed
(~ 30 cm/s)
Air-flow Speed
Ferkul, P.V. and Olson, S.L., “Zero-gravity Centrifuge Used for the Evaluation of material Flammability in Lunar-Gravity,” AIAA
2010-6260, 40th International Conference on Environmental Systems, Barcelona, Spain, July 11-15, 2010.
12
Saffire-II Samples
• International Topical Team members from Bremen, Germany are conducting
ground tests of one of the samples to be flown on Saffire-II.
• This is a polymethyl methacrylate (PMMA) sheet with a machined ridges and
grooves on the surface
• This will investigate the influence of surface structure on the spread rate of a
low-g flame
Images obtained using an infrared (IR) camera of a flame on structured PMMA
sample. The design of structures machined into the sample are shown below each
image. The effect of edge curvature and type of structure on the flame is evident.
These results were obtained in 1-g after 60 seconds for all images.
13
Modeling
• Xiaoyang Zhao and Prof. James T’ien
(Case Western Reserve University) are
expanding the capability of an existing
flame spread model to simulate Saffire
test conditions.
• Data from Saffire-I, -II, and –III
experiments will be compared to
extended versions of these models.
Buoyant flow sample is
5 cm wide by 30 cm
long, sandwiched by
metal plates
g
g
Temperature along center plan (colors) vs.
time (top to bottom) for a buoyant flow
condition. (In low-g, Saffire conditions will
be in forced flow.)
14
Result: Saffire-II --- Array of 9 samples
1
3
4
5
6
7
♦ Samples are 5 cm x 29 cm
2
8
9
♦ Four different sample materials
• Concurrent and opposed for Silicone
♦ Motivation
• Previous low-g data (small scale)
• Material flammability limits
• NASA-STD-6001 Test 1
• Spacecraft fire safety strategy
PMMA
Silicone
SIBAL
Silicone
(opposed)
Nomex
17
Saffire-II: Array of 9 samples
Sample #
Material
Sample
Thickness
Saffire-2-S1
Flam limit 1
Silicone
0.25 mm (0.010”)
Silicone
20
Saffire-2-S2
0.36 mm (0.014”)
Silicone
20
Saffire-2-S3
0.61 mm (0.024”)
Silicone
20
Silicone down
0.36 mm (0.014”)
Silicone
20
N/A
20
SIBAL
N/A
Bottom
Transition 1:
PMMA to
NOMEX
N/A
20
Bottom
Structured
PMMA
10 mm with
tapered edge for
ignition
20
Bottom
PMMA
10 mm with
tapered edge for
ignition
20
9
Bottom
Velocity of
Saffire-III
(30)
8
Top
SIBAL
6
Bottom
Saffire-2-S4
5
Bottom
Flam limit 3
Silicone
3
Bottom
Flam limit 2
Silicone
2
7
Igniter
Position
1
4
Flow (cm/s)
Bottom
Saffire-2-S5
(Compares
with Saffire-I)
Saffire-2-S6
(Compares
with Saffire-III)
Saffire-2-S7
Saffire-2-S8
Saffire-2-S9
18
Science Status
Saffire-II Sample Card
•
Populated and wired sample card for Saffire-II
• Igniter wire “loops” on a silicone sample
‒ Space upstream of sample allows
edge ignition
Flow
19
Conclusions
♦ Through novel utilization of an existing carrier, Saffire has broken
the path for a new research platform.
♦ Saffire tests exceed (in size) all prior low-gravity combustion
testing by more than an order of magnitude, bringing the flames
to a realistic scale.
♦ Saffire results will provide an important benchmark data set for
future space craft fire safety design and analysis.
18 [E-81123adcd59c0ce9]
- Saffire: A Novel Approach to Study of Spacecraft Fire Safety Using Un-Manned Spacecraft — recorded page 1 (physical PDF page unverified): affire-I burned for 400 sec
• Saffire-III burned for 320 sec.
♦ This is equal to the inverse ratio of the flame speed
 The flame speed is proportional to the air flow velocity
♦ Comparison of the
opposed (upper) and
concurrent (lower)
flames from Saffire-III.
• The flame images
were taken at
different times (near
the end of each burn)
and superimposed.
16
Saffire-I-III Results
Measurements of flame base (up stream), pyrolysis tip
(downstream), and pyrolysis length from concurrent and
opposed burns from Saffire-I.
Spread rate summary for Cotton/Fiberglass fabric burning in
microgravity
17
Saffire-I-III Results
♦ Flame spread over a large thin charring surface in low-gravity
showed that steady flame spread was possible (unlike normal
gravity).
♦ Concurrent flame spread (with the wind) was shown to be more
sensitive to the flow duct dimension than previously anticipated.
♦ Large scale experiments could be safely conducted in an un-manned
spacecraft.
A new series of experiments was proposed to extend the impact to the
vehicle, examine thick materials and consider detection and post-fire
cleanup
18
Saffire-IV, V, and VI Concept
Objectives:
♦ Demonstrate spacecraft fire monitoring and cleanup
technologies in a realistic spacecraft fire scenario
♦ Characterize fire growth in high O2,
low pressure atmospheres
♦ Provide data to validate models of prediction of the
impact of a fire on vehicle habitability
Far Field Diagnostics
Saffire Flow Unit
Approx. 53x90x133cm. New features
include 2 side view cameras, acid gas,
O2, heat and byproduct release to cabi
Saffire Flow Unit
Remote Sensors (6)
Measure temp & CO2 in standoffs,
hatch and end cone
Remote Sensors
[6 total, 2 end cones, 4
central]
Far Field Diagnostics (in Mid Deck Locker)
Avionics, CO2 scrubber, Smoke Eater, combustion product
and smoke sensors
19
Forward Steps
• The Saffire experiments were the first practical-scale spacecraft fire safety
investigations.
• In addition to pioneering a new research capability, they determined that
concurrent flames can achieve a steady spread rate and that overall the
concurrent spread rates are strongly influenced the the flow duct size.
• The next Saffire series will examine larger fires of longer duration to
examine the impact of a fire on the vehicle habitability .
20
21
Backup
22
Four tests:
40.6-cm-wide SIBAL fabric (cotton-fiberglass); concurrent and opposed-flow in 20 cm/s air flow
5-cm-wide SIBAL fabric; concurrent-flow in air at 20 and 25 cm/s
Saffire 1
Saffire 2
SIBAL fabric
5 cm wide
SIBAL fabric
40.6 cm wide
Ignition power:
Saffire 1: 165 W (for 8 s)
4.1 W/cm (per unit fuel width)
Saffire 2: 80 W (for 9.2 s)
16 W/cm (per unit fuel width)
Average flame power:
Saffire 1: 1200 +/- 300 W
Saffire 2: 200 +/- 50 W
Fuel characteristics (“SIBAL” fabric)
75% cotton, 25% fiberglass blend
Simple weave pattern (60 x 40 threads per inch)
Cotton and fiberglass fibers intermingled
Overall area density: 18 mg/cm2
Fuel sizes (W x L): 40.6 x 94 cm and 5 x 29 cm
Saffire 1 video
SIBAL fabric (40.6 cm x 94 cm) burning in air at 20 cm/s concurrent flow
Average flame spread rate is 1.8 mm/s; estimated average flame power is 1200 +/- 300 W
Total burn time is 420 s
25
Plots of igniter current and thermocouple temperatures. X-distance along the sample for each
thermocouple is shown on the diagram. Heights above the surface are indicated on the plot.
26
27
28
29
Sample
I-1
Table 1. Summary of Samples, Test Conditions, and Selected Results
Material
Width
Thickness
Length
Flow
Direction
Cotton-Fiberglass
40.6 cm
0.37 mm
94 cm
20 cm/s
Concurrent
Δ %O2 i
21.7 to 21.5
I-2
Cotton-Fiberglass
40.6 cm
0.37 mm
~ 10 cm
20 cm/s
Opposed
~ 21.5
II-1
Silicone
5 cm
0.27 mm
29 cm
20 cm/s
Concurrent
~ 22.1
II-2
Silicone
5 cm
0.61 mm
29 cm
20 cm/s
Concurrent
~ 22.1
II-3
Silicone
5 cm
1.03 mm
29 cm
20 cm/s
Concurrent
~ 22.1
II-4
Silicone
5 cm
0.37 mm
29 cm
20 cm/s
Opposed
~ 22.1
II-5
Cotton-Fiberglass
5 cm
0.37 mm
29 cm
20 cm/s
Concurrent
~ 22.1
II-6
Cotton-Fiberglass
5 cm
0.37 [E-ad149b6a9ce7f2f8]
- Operation and Development Status of the Spacecraft Fire Experiment (Saffire) — recorded page 1 (physical PDF page unverified): Advanced Exploration Systems Division
Operation and Development
Status of the Spacecraft Fire
Experiment (Saffire)
Gary A. Ruff and David L. Urban
NASA John H. Glenn Research Center
Cleveland, OH
July 13, 2016
International Topical Team

Sandra Olson, NASA Glenn Research Center, Cleveland, OH

Paul Ferkul, NASA Glenn Research Center, Cleveland, OH

Carlos Fernandez-Pello, UC Berkeley, Berkeley, CA, USA

James S. T’ien , Case Western Reserve University, Cleveland, OH, USA

Ya-Ting Liao, Case Western Reserve University, Cleveland, OH, USA

Jose L. Torero, University of Queensland, Brisbane, Australia

Guillaume Legros, Université Pierre et Marie Curie, Paris, France

Christian Eigenbrod, University of Bremen (ZARM), Bremen, Germany

Nickolay Smirnov, Moscow Lomonosov State University, Moscow, Russia

Osamu Fujita, Hokkaido University, Sapporo, Japan

Sebastien Rouvreau, Belisama R&D, Toulouse, France

Balazs Toth, ESA ESTEC, Noordwijk, Netherlands

Grunde Jomaas, Technical University of Denmark, Kgs. Lyngby, Denmark
2
Spacecraft Fire Safety Demonstration
•
Project Background and Objectives
•
Saffire Hardware
•
Flight Operations
•
Preliminary Results
•
Spacecraft Fire Safety Technology Needs
•
Saffire-IV-VI Objectives and Plans
3
Saffire-I, II, & III Overview
Needs:

Low-g flammability limits for spacecraft
materials

Definition of realistic fires for exploration
vehicles
Fans
Power
Management
Sample card
(flame spread
sample
shown)
‒ Fate of a large-scale spacecraft fire
Objectives:


Saffire-I: Assess flame spread of largescale microgravity fire (spread
rate, mass consumption, heat
release)
Saffire-II: Verify oxygen flammability limits
in low gravity
Cameras
Avionics Bay
Signal
conditioning
card

Saffire-III: Same as Saffire-I but at different
flow conditions.
•
Data obtained from the experiment will be used to
validate modeling of spacecraft fire response
scenarios
Evaluate NASA’s normal-gravity material
flammability screening test for low-gravity conditions.
•
Flow Duct
Flow
straightener
Saffire module consists of a flow duct
containing the sample card and an
avionics bay. All power, computer, and
data acquisition modules are contained
in the bay. Dimensions are
approximately 53- by 90- by 133-cm
4
Sample Card Holder Configurations
 Sample card and samples are the only differences between the three
flight units
Saffire-I, -III Sample Card
Composite fabric (SIBAL cloth)
(75% cotton – 25% fiberglass by mass)
(0.4 m x 0.95 m)
Saffire-II Sample Card
Saffire-II Samples (5 cm x 29 cm)
•
PMMA (flat and structured)
•
Silicone (3 thicknesses, different
ignition direction)
•
SIBAL
•
Nomex (with PMMA ignition)
5
Operations Concept
Pre-Launch
Unpowered
Inhibits Open
Powered
Inhibits
Closed
Hawaii
WGS
66
Saffire-I Integration
January 2016
Saffire-I hardware
strapped into the
Cygnus Pressurized
Cargo Module
Saffire-I
Integration.
NASA-KSC
7
Saffire-I Launch and Berthing
March 22
 Successful launch of Saffire-I onboard Cygnus OA-6 (SS Rick Husband) on
March 22
 Orbital ATK reported that OA-6 had a nominal ascent.
‒
Spacecraft Mission Director reported to the Saffire team “Vehicle is good. PCM is
good. All inhibits in place. Enjoy the ride.”
Saffire-I photograph taken
by the ISS crew following
initial ingress to the PCM
Launch of OA-6 on
March 22 carrying
Saffire-I
 OA-6 Pressurized Cargo Module (PCM)
berthed to the ISS on Saturday, March 26
with crew ingress into the PCM on March 27
 The crew took on-orbit photographs of
Saffire-I (right)
8
Saffire-I Operations
June 14-20, 2016
 OA-6 unberthed from the ISS at 9:30
a.m. EDT on June 22
 Saffire-I was powered on at 2:23 p.m.
 RUN command was sent at 4:41 p.m.

Ignition at 4:44 p.m.
 Cygnus smoke detector readings
received at 4:52 p.m.
NASA and Orbital ATK teams at MCC-Dulles
(above) and Flight Operations-GRC (right)
conducted and monitored Saffire-I operations
 Operations received considerable
coverage on social media

NASA GRC and AES
9
Saffire-I Operations
Smoke [E-5d4bb0be10b6a4a3]
- Results of Large-Scale Spacecraft Flammability Tests — recorded page 1 (physical PDF page unverified): he vehicle was guided for destructive re-entry into the Earth’s atmosphere.
5
Air Flow
29 cm
5 cm
The Saffire flow duct (18” x 20”). Two cameras and four
radiometers are indicated. Camera and radiometer fields of
view are shown by the cones, shaded blue and red, respectively.
Saffire-II sample card with the
nine samples, and ignition
locations are indicated in red.
There were six sample thermocouples per flight.
7
Configurations
Saffire 1
Saffire 2 (samples 5 cm wide)
Silicone
Ignition power:
Saffire 1: 165 W (for 8 s); 4.1 W/cm (per unit fuel width)
Saffire 2, all samples except thick PMMA:
SIBAL fabric
80 W (for 9.2 s); 16 W/cm (per unit fuel width)
Saffire 2, thick PMMA:
97 W (for 30 s); 19.5 W/cm (per unit fuel width)
Thin PMMA/Nomex®
SIBAL fabric
40.6 cm wide
Thick PMMA
Average flame power:
Saffire 1: 1200 +/- 300 W
Saffire 2: (SIBAL fabric) 200 +/- 50 W
Saffire 2: (Thick PMMA) 600 +/- 100 W
Saffire-2 Description
2-1
2-2
2-3
2-4
Nine samples; 5 cm wide by 29 cm long
20 cm/s flow for all tests except for Sample 2-6 (25 cm/s)
All upward burns except Sample 2-4 was downward
Initial oxygen concentration 22.1% (ISS reading,
slightly higher than Saffire-1’s 21.7%)
2-5
2-6
2-7
2-8
2-9
Samples 2-1 to 2-4 were silicone sheets 0.27, 0.61, 1.03, and 0.37 mm thick.
Samples 2-5 and 2-6 were cotton-fiberglass fabric identical to that used in Saffire-1.
Sample 2-7 had a composite construction, the first 5 cm of which was a thin (0.8 mm)
sheet of PMMA and the remainder Nomex® fabric (HT 90-40).
Samples 2-8* and 2-9* were PMMA slabs with a nominal thickness of 1 cm. Sample
2-8 had some surface features, including a groove down the center (in the flow
direction) on both sides, while Sample 2-9 was flat.
* Results from these samples are described in another paper at this conference.
9
Saffire-2 Description (con’t)
2-1
2-2
2-3
2-4
2-5
2-6
2-7
2-8
2-9
Thick PMMA Sample cross sections:
The middle 1.8-cm-wide portion of Sample 2-8 is
only 0.4 cm thick.
The ignition energy and time for samples 2-1 through 2-7 were chosen to mimic the
NASA 6001 Test 1 ignition, 736 J applied uniformly for 9.2 s.
Samples 2-8 and 2-9 had slightly more powerful igniters (97 W instead of 80 W) and
were left on longer (30 s instead of 9.2 s) to assure ignition of these thick fuels.
10
Saffire-2; Why Silicone?
Upward burning silicone samples (2-1 to 2-3) were 0.27, 0.61, and 1.03 mm thick.
In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.
In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn.
Microgravity behavior was sought:
‒ How much of the available fuel would be burned?
‒ Would microgravity prove more or less favorable to flame spread?
11
Saffire-2; Silicone Results
Results were convincing although rather anticlimactic as none of the silicone samples burned.
When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly
extinguished. The igniters all appeared to function normally and the materials were clearly damaged in
the vicinities of the igniters.
It was surprising that not even the thin sample could permit any flame spread, given that it was entirely
consumed in normal gravity. Previous experience with cellulosic fuels (paper and fabric) and even
PMMA suggested that if a flame could persist in upward 1-g tests then it would also burn in
microgravity at a moderate flow speed which was less than that typical in buoyant flow.
12
Saffire-2; Silicone Results (con’t)
The behavior of silicone in microgravity is perplexing perhaps due to its complex burning:
‒ Silicone produces fine silica  [E-49fde889c36ce643]
- Determining Flame Temperature By Broadband Two Color Pyrometry in A Flame Spreading Over A Thin Solid in Microgravity — recorded page 1 (physical PDF page unverified): n-
vironments, NASA embarked on a research project,
the Spacecraft Fire Experiment (Saffire) [3], that aims
to better understand material flammability and fire
growth and spread. The Saffire experiments are a se-
ries of unique and novel large-scale spacecraft exper-
iments performed on board the Cygnus cargo space-
craft, after the vehicle has completed its primary mis-
sion to the ISS, and before its planned destructive
reentry through Earth’s atmosphere. Using this ve-
hicle to perform large-scale fire experiments was an
innovative way to use a microgravity facility and al-
leviated the concern of crew safety for a large fire
experiment. The Saffire experiments have been dis-
cussed and documented previously, and the reader is
referred to Refs. [3–5] for further details. The re-
sults of the tests performed have shown that space-
craft fires could grow significantly, release enough
heat and toxic gases, and persist long enough to be
of concern to the crew and the spacecraft.
Despite efforts to better understand fire spread
mechanisms in microgravity environments, the prob-
lem is still poorly understood [6]. Traditionally, flame
spread over solid fuels has been studied in micro-
gravity by means of tracking the flame or the pyrol-
ysis front, providing useful but limited information
of the process. As the flame spreads over the solid
fuel, it acts both as the source of heat needed to py-
rolyze the virgin fuel and as a pilot that later ignites
the flammable mixture formed after the pyrolyzates
mix with the oxidizer (see Fig. 1). Knowledge of the
radiative properties of flames, in particular the tem-
perature, are important to better understand the gen-
eral process, particularly near extinction [7, 8]. Here,
color pyrometry provides a useful method to deter-
mine the temperature of the flame without disruptions
to the spread process. Previous studies have taken ad-
vantage of these techniques when studying diffusion
flames on gas burners [9–12], however only recently
the technique has been applied to spreading flames
[13–15].
The results obtained during the Saffire IV experi-
ments are revisited here to provide further informa-
tion about the characterization of the flames observed
during this unique experiment. Raw images obtained
during the tests are analyzed to determine the temper-
ature of the flame using broadband two color pyrome-
try (B2CP). It is expected that the results of this work
will provide further insight into unique data obtained
during microgravity experiments. Furthermore, this
methodology could complement point measurements
traditionally performed, providing a more complete
view of the flame temperature to be used for the
validation of numerical models in microgravity, and
thus shedding light onto the additional processes that
might play a dominant role in the spread of the flame.
Fig. 1: Diagram of concurrent flame spread over a thin sam-
ple. Only half of the flame is schematized (symmetry is as-
sumed with respect to the sample center plane).
2. Experimental setup
The data presented here correspond to experimen-
tal data obtained as part of the Saffire IV experiments
[5] performed by NASA on board the resupply ve-
hicle Cygnus CRS-15 before its destructive re-entry
through Earth’s atmosphere. A brief description about
the experimental setup and procedure is given here.
For further information, the reader is referred to Refs.
[3, 5]. The hardware, shown in Fig. 2, was a rect-
angular flow duct measuring 15 cm (perpendicular
to the sample surface) by 45 cm width and 109 cm
length. The duct was equipped with a fan at the in-
let section to induce the flow of air through the flow
duct, a vane anemometer at the entrance of the in-
let duct was used to monitor the flow velocity. The
inlet and outlet of the duct was equipped with flow
straighteners that connected to a plenum parallel to
the flow duct, resulting in a folded geometry. This
geometry favored flow mixing and enabled oxygen,
carbon dioxide, and c [E-20d4518a07dc9870]
- Operation and Development Status of the Spacecraft Fire Experiment (Saffire) — recorded page 1 (physical PDF page unverified): e-I (right)
8
Saffire-I Operations
June 14-20, 2016
 OA-6 unberthed from the ISS at 9:30
a.m. EDT on June 22
 Saffire-I was powered on at 2:23 p.m.
 RUN command was sent at 4:41 p.m.

Ignition at 4:44 p.m.
 Cygnus smoke detector readings
received at 4:52 p.m.
NASA and Orbital ATK teams at MCC-Dulles
(above) and Flight Operations-GRC (right)
conducted and monitored Saffire-I operations
 Operations received considerable
coverage on social media

NASA GRC and AES
9
Saffire-I Operations
Smoke Flow Visualization (Pre-Test)
 Smoke line
visualization of the
flow in the Saffire-I
duct.
• (Top) smoke line
image with lens
distortion.
• (Bottom) Image
with distortion
correction
showing later
smoke lines.
• The flow is from
right to left.
Camera 1 and 2 images as recorded (with distortion)
Flow
Camera 1 and 2 images with distortion correction
10
Saffire-I Operations
Concurrent Flow Igniter
Igniter
Thermocouple
wires
Flow
40 cm
Thermocouple
beads
Thermocouple wire woven
into the fabric to assess
flame structure
Thermocouple
beads
Saffire-I sample material at the beginning of the concurrent (upstream) burn.
Thermocouple wires are sewn into the sample material with thermocouple beads at
various heights in the center of the sample.
11
Saffire-I Operations
Concurrent Flow Igniter
40 cm
Flow
Video of the first 30 seconds of the Saffire-I concurrent (upstream) burn. The
green LED is on for 1 second and off for two seconds (1 second out of three). Shorter
times indicate missing downlinked frames.
12
Saffire-I Operations
So, how big is the flame?
The length of the
Saffire-I sample is 94 cm;
the BASS sample is 7 cm
long
40 cm
Flow
2.2 cm
Saffire-I flame compared to a flame from the Burning and Suppression of Solids (BASS)
experiment conducted in the Microgravity Science Glovebox . Camera exposures and gains
are different between the two experiments.
13
Saffire-I Operations
Opposed Flow Igniter
Igniter
Unburned
sample
Thermocouple
wires
Thermocouple
beads
40 cm
Saffire-I sample material at the beginning of the opposed flow (downstream) burn. The light
portion of the image is sample material unburned from the concurrent burn. A second set of
thermocouple wires are sewn into the sample material with thermocouple beads at various heights
14
in the center of the sample.
Saffire-I Operations
Opposed Flow Igniter
Flow
40 cm
Video of the Saffire-I opposed flow (downstream) burn. The green LED is on for 1 second and
off for two seconds (1 second out of three). Shorter illumination durations indicate missing
downlinked frames.
15
Saffire-I
End-of-Mission
 Saffire-I relays were opened at 9:41:48 p.m. on June 19, 2016 ending the
mission
 Cygnus OA-6 deployed CubeSat experiments on June 20
 Cygnus de-orbited on June 21, 11:29 p.m.
Saffire-I Future Analysis
 Location of pyrolysis front, flame base, and flame length vs. time for concurrent
and opposed flame spread (rate of flame spread)
 Pulsation frequency of the concurrent flame
 Comparison with computational models of the concurrent and opposed flow
flames
 Pressure and temperature rise of the Cygnus vehicle during combustion
 Transport of smoke aerosol in the Cygnus vehicle
 Estimate of the free volume of the Cygnus vehicle
 Impact on operation of Saffire-II and III
 Analyses will be performed by researchers from NASA and the International
Topical Team and published in various papers
 Data will also be posted to NASA Physical Sciences Informatics System
(psi.nasa.gov)
Saffire-II
Samples
 Samples are 5 cm x 29 cm
1
2
3
4
5
6
7
8
9
 Four different sample materials
• Concurrent and opposed for
Silicone
 Motivation
• Previous low-g data (small scale)
• Material flammability limits
• NASA-STD-6001 Test 1
• Spacecraft fire safety strategy
 Thermocouples mounted on the
SIBAL and Nomex samples
 Saffire-III sample material will be the
same as Saffire-I

Flow will be close to 30 cm/sec as
opposed to 20 cm/sec for Saffire-I
Silicone
SIBAL
Silicone
(opposed)
PMMA
Nomex
Spacecraft Fire Safety Dem [E-772994a1417846a7]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Concurrent and opposed-flow comparison; https://ntrs.nasa.gov/citations/20170008805 [E-context-0bacb5f04c6c34659dcc]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-I Description and SIBAL results; https://ntrs.nasa.gov/citations/20170008805 [E-context-7973df3a5b7f8b12b64d]
- Operation and Development Status of the Spacecraft Fire Experiments (Saffire) — ntrs-20170000230, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170000230 [E-1ac66b2fe73347e1]
- Determining Flame Temperature By Broadband Two Color Pyrometry in A Flame Spreading Over A Thin Solid in Microgravity — ntrs-20220012861, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20220012861 [E-18c496f0304c63ce]
- Spacecraft Fire Safety Demonstration — ntrs-20160010292, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20160010292 [E-81123adcd59c0ce9]
- Saffire: A Novel Approach to Study of Spacecraft Fire Safety Using Un-Manned Spacecraft — ntrs-20180005168, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20180005168 [E-ad149b6a9ce7f2f8]
- Operation and Development Status of the Spacecraft Fire Experiment (Saffire) — ntrs-20170002628, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170002628 [E-5d4bb0be10b6a4a3]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170008805 [E-49fde889c36ce643]
- Determining Flame Temperature By Broadband Two Color Pyrometry in A Flame Spreading Over A Thin Solid in Microgravity — ntrs-20220012861, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20220012861 [E-20d4518a07dc9870]
- Operation and Development Status of the Spacecraft Fire Experiment (Saffire) — ntrs-20170002628, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170002628 [E-772994a1417846a7]
- Saffire-I — psi-98, CSV, row 2; https://lsda.jsc.nasa.gov/Experiment/PSI-98 [E-psi-98-table-S1]
- Saffire-I — psi-98, CSV, row 3; https://lsda.jsc.nasa.gov/Experiment/PSI-98 [E-psi-98-table-S2]



## What happened after airflow was interrupted and restored?

QueryIntentV2 constraints: `[]`; requested classes: `['ReportedObservation', 'Intervention']`. Effective gravity policy: `{'enabled': True, 'explicit_values': [], 'comparative': False, 'default_preference': ['microgravity'], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['context:saffire-iv-flow-intervention', 'context:saffire-iv-flow-observation']. RELATED: ['context:bass-film-observation', 'context:bass-flight-rod-observation', 'context:bass-ground-rod-observation']. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.
Research preference: microgravity. Experimental conditions are established by the cited sources.

## Applicable scientific context

- gravity: microgravity; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37].
- apparatus: context:bass-wind-tunnel; applies to context:bass-film-observation. The group statement and verified membership establish applicability [E-context-5227141f2aaa7feb2e37, E-context-e6623c40985279bec3b2].
- gravity: microgravity; applies to context:bass-flight-rod-observation, context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
  Exceptions: context:bass-ground-rod-observation
- material: PMMA; applies to context:bass-flight-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:saffire-iv-flow-observation, context:saffire-iv-flow-intervention. The group statement and verified membership establish applicability [E-context-3b27486ede2bf8151a2f, E-context-d1e50788b120206316a0].
- gravity: normal-gravity; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- material: PMMA; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37].
- oxygen: 21%; applies to context:bass-ground-rod-observation. The group statement and verified membership establish applicability [E-context-d0e9f6c262d92e57e3bd].

## Direct evidence

- context:saffire-iv-flow-intervention [E-context-3b27486ede2bf8151a2f, E-context-80d7fc00aae08504c315]
  Matches: ['reviewed requested information class']; differs: []; unknown: []; invalid: [].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:saffire-iv-flow-observation [E-context-80d7fc00aae08504c315, E-context-d1e50788b120206316a0]
  Matches: ['reviewed requested information class']; differs: []; unknown: []; invalid: [].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
Related evidence: 1 condition groups representing 3 candidates. All candidate IDs and citations remain available in the evidence bundle.

## Related evidence

- context:bass-film-observation [E-context-5227141f2aaa7feb2e37, E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2]
  Applicability limits: requested_event_not_established:restored; requested_event_not_established:interrupted
  Matches: ['reviewed requested information class']; differs: []; unknown: []; invalid: [].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Reported observations

- Sequence of top views showing radiative quenching when
flow velocity goes below 2 cm/s.

Flame nearing blow off extinction as the flow
velocity crosses 40 cm/s. [E-context-90f697823c2ba1b2ea82, E-context-e6623c40985279bec3b2, E-context-5227141f2aaa7feb2e37]
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
- There is a downward trend in flame
spread rate as sample diameter increases
for both the 1g and μg (microgravity)
tests. 1g tests have higher flame spread
rates than μg.

1g Black

Flame Spread Rate [cm/sec]

Flame spread rate as a function of
sample diameter for both 1g and μg
tests. 1g tests are in natural convection
at 21% oxygen environments. Values for
μg tests are averaged over flow velocity
and oxygen concentration. [E-context-d0e9f6c262d92e57e3bd, E-context-87d3a70a788ae398fe4a, E-context-5227141f2aaa7feb2e37]
- The fire didn’t extinguish and began to grow when we 
turned the flow back on [E-context-d1e50788b120206316a0, E-context-80d7fc00aae08504c315]

## Experimental interventions

- For the Saffire-IV PMMA sample, we turned off the 
flow for 20 seconds [E-context-3b27486ede2bf8151a2f, E-context-80d7fc00aae08504c315]

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Flammability Aspects of a Cotton-Fiberglass Fabric in Opposed and Concurrent Airflow in Microgravity — recorded page 1 (physical PDF page unverified): s
to Higher Flow
Airflow
Changes
Experiment Operation:
Flame Extinction
(Flow reduced too far
or fuel consumed)
Airflow
Hardware Summary:
Sample Images
 BASS utilized the on-orbit SPICE hardware;
minor modifications were made to burn solid
samples
Digital Still
Video
 Small flow tunnel
 Solid samples were installed, ignited,
extinguished, and recorded
 Video and digital still camera provided bulk
of the data. Flame appearance, behavior,
spread rate, and extinction dynamics were
measured
 Airflow speed was the main variable
Airflow
Fuel characteristics (“SIBAL” fabric)
25% fiberglass, 75% cotton blend
Simple weave pattern (60 x 40 threads per inch)
Cotton and fiberglass fibers intermingled
Overall area density: 18 mg/cm2
Fuel sizes: 8.5 cm length; 1 and 2 cm width
Airflow
Video (edge view) of 2-cm-wide sample in concurrent flow. Ignition is obtained
at an airflow speed of 10 cm/s and flow is then reduced to 5 cm/s.
Effect of flow speed on 2-cm-wide sample in concurrent flow (top view)
10 cm/s Airflow
5 cm/s Airflow
10 cm/s Airflow
1 cm
Digital still camera images for 1-cm-wide fuel with concurrent airflow = 10 cm/s.
Images are taken every 1.125 sec (starting at bottom and moving from left to right).
The flame reaches steady state after about 10 seconds.
Still image analysis; 1 cm-wide fuel, 10 cm/s airflow
180
20
170
18
160
Flame Base Position
16
140
130
Flame Length
14
120
110
12
100
90
10
80
8
70
60
xtip = 1.71 t + 2.25
50
6
40
4
30
xbase = 1.68 t - 13.81
20
2
10
0
0
0
10
20
30
Time, s
40
50
60
Flame Length, mm
Flame Tip and Base Position, mm
150
Flame Tip Position
10 cm/s Airflow
2 cm
Digital still camera images for 2-cm-wide fuel with opposed airflow = 10 cm/s.
Images are taken every 1.25 sec (starting at top and moving from left to right).
Flame quickly reaches steady state and goes out when it runs out of fuel.
Note: Downward flame spread (opposed flow) in 1-g with this material is not
possible in normal air.
10 cm/s
6 cm/s
Airflow
4 cm/s
2 cm/s
1.5 cm/s
1 cm/s
Digital still camera images showing a flame burning a 2-cm wide cotton-fiberglass
fabric in opposed flow. Images are taken every 1.25 sec (starting at top and moving
from left to right). The flow is decreased in discrete steps from 10 cm/s all the way
down to about 1 cm/s. The flame response to flow changes is very rapid, and the flow
effects on the flame and its spread rate are dramatic. Total burn time is 90 sec. Flow
changes are indicated by numbers.
Airflow
Video view of 2-cm-wide sample in opposed flow. Blowoff is attempted at high
flow speed (~44 cm/s).
Concurrent and Opposed Spread at ~ 10 cm/s
2.55 mm/s versus 1.21 mm/s
10 cm/s Airflow
6
2 cm concurrent
1 cm concurrent
5
Flame Spread Rate, mm/s
2 cm opposed
VF = - 0.20 U∞ + 0.56
4
3
VF = - 0.15 U∞ + 0.07
2
1
Extinction
0
-50
-40
-30
-20
-10
0
10
Forced Flow Velocity, cm/s
20
30
40
50
Comparison of 0-g and 1-g Concurrent Flow Flames
0-g with flow (10 cm/s)
Steady flame size and spread
Convex base
Extended blue zone
1-g with flow (10 cm/s)
Growing flame size and spread
Concave base
Extended soot zone
Comparison of 0-g and 1-g Opposed Flow Flames
0-g with flow (10 cm/s)
Steady flame size and spread
Convex base
Extended blue zone
1-g
Flame does not propagate downward
Summary
♦ For the opposed flow configuration, the flame quickly reached steady
spread for each flow speed, and the spread rate was fastest at an
intermediate value of flow speed.
♦ These tests show the enhanced flammability in microgravity for this
geometry, since, in normal gravity air, a flame self-extinguishes in
the opposed flow geometry (downward flame spread).
♦ For the concurrent flow configuration, a limiting length and steady
spread rate were obtained only in low flow speeds. For these
conditions, flame spread rate increased linearly with increasing flow.
♦ This is the first time that detailed transient flame growth data was
obtained in purely forced flows in microgravity. In addition, by
decreasing concurrent flow speed to a very low [E-1bc76d1f2a957fd8]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): spectacular views.
936
4
Here is a quick layout of the laboratory; this did not include, of course, the middeck experiments.
We have the control center rack, the rack that had our four VCRs on it which recorded much of our
video data; the Drop Physics Module complex where we saw some of the data generated today with the
acoustical chamber; a rack called SMIDEX that allowed us to carry experiments that could be carried
from middeck as well; the Solid Surface Combustion Experiments; and the Generic Bioprocessing
Apparatus, as well as some of the EDOMP experiments. The other components are the Glovebox,
which is just as valuable for supporting some of the experiments, the Crystal Growth Furnace in its
complex; from Case Western and Lewis, the Surface Tension-Driven Convection Experiment; and next
to that the rack used as a work bench with a table, supplies, and stowage. We had a number of center
aisle stowage containers as well.
On the first day on orbit Larry and I started work loading the CGF. Then Larry started working
back at the Glovebox. We were surprised to open up the CGF sample container and see an American
flag there. We were very proud of the mission, but also proud since we were going to be up on the fourth
of July. Larry worked many long hours at the Glovebox doing his protein crystal growth. He was very
dedicated to that and I think the results show that. On the other shift, Carl also worked very hard at the
Glovebox on many of the proteins as well. On the blue shift, Gene spent many hours at the drop
physics module. You see lots of cables and wires and that is part of living in a zero-gravity environment.
Without Velcro which were the white patches on the door and straps holding cables back, it is a little bit
of a chaotic environment. We did hang up the flag for the fourth of July celebration. One of Carl's very
favorite experiments was the Generic Bioprocessing Apparatus and here he is wearing the pressure as
part of his physiological experiments. This is the candle burning experiment. I think this was exciting for
all of us and both Carl and I had an opportunity to do that. This is probably one of the most popular
slides I show when I go out and talk because it is a dramatic demonstration, for most people, on the
difference between gravity and microgravity. Most people know what a birthday candle looks like. They
think of how it ought to burn in low gravity and here is what it actually does. Larry and I spent many hours
as subject and operator for the lower body negative pressure device. We both trained on operating the
I
Echocardiographthe device that is used to image the heart, and we used Doppler to measure the blood
flow velocities, it's all recorded on 8 mm tapes. It is an interesting type of work and I certainly enjoyed it
and we got a lot of good data out of it. We looked at fluids we wanted to stabilize. We looked at fluid
I
interfaces that we wanted to bifurcate. This particular experiment is the Drop Physics Module; I
understand it had most of control mission hypnotized for the entire flight if you happened to watch any Of
those drops. When I talk to my friends at JSC that is the single thing they remember the most.
We saw some spectacular sights form orbit, we saw sunrises and sunsets, we looked at a lot Of
water, and many islands. We monitored some flooding in South America. I know this is a rather hazy
937
I
b
picture, but there is some significant river flooding and we were asked on real time to document that on
orbit. We documented deserts and we looked at dust storms coming over the Atlantic off the coast of
Africa. Any time you take over 4000 pictures on a flight it is a little difficult to find all the best ones to
show. But certainly, this gives you a little flavor of the view we had from orbit.
This flight ended over a year ago from now. Here we look at the data and we are looking at the
future of where we are going. We have been through some rather interesting months on the space
station and [E-1a048dade39a6ea2]
- Research and Technology 1999 — recorded page 1 (physical PDF page unverified): ill be accomplished by first
pointing both antennas at the
satellite using information from the
aircraft data bus. Then, the system
phased-array controller will electronically adjust the antenna pointing of the receiving antenna to find
the peak signal. After the peak signal has been found, the beam of
the transmitting antenna will be
pointed to the same steering
angles as the receiving antenna.
For initial ground testing without
an aircraft, the ARINC 429 data bus
(ARINC Inc., Annapolis, Maryland)
will be simulated by a gyro system
purchased for the follow-on to the
Monolithic Microwave Integrated
Circuit (MMIC) Arrays for Satellite
Communication on the Move
(MASCOM) Project. MASCOM
utilized the Advanced Communications Technology Satellite (ACTS)
with a pair of Ka-band experimental phased-array antennas.
Glenn contact:
Robert J. Zakrajsek, (216) 433-3487,
Robert.J.Za krajsek@grc.nasa.gov
Author: Robert J. Zakrajsek
Headquarters program office: OAST
Programs/Projects: AC/ATM
It is well known that fires in the low-gravity environment of Earth-orbiting
spacecraft are different from fires on Earth. The flames lack the familiar
upward plume, which is the result of gravitational buoyancy. These flames,
however, are strongly influenced by minor airflow currents. A recent study
conducted in low gravity (microgravity) on the Russian orbital station
used burning plastic rods mounted in a small chamber with a controllable
fan to expose the flame to airflows of different velocities. In this unique
project, a Russian scientific agency, the Keldysh Research Center, furnished
the apparatus and directed the Mir tests, while the NASA Glenn Research
Center at Lewis Field provided the test materials and the project management. Reference testing and calibrations in ground laboratories were conducted jointly by researchers at Keldysh and at the NASA Johnson Space
Center’s White Sands Test Facility.
ultiple samples of three different plastics were burned in the tests: Delrin,
a common material for valve bodies; PMMA, a plastic “glass”; and polyethylene, a familiar material for containers and films. Each burned with a
unique spherical or egg-shaped
flame that spread over the rod.
The effect of varying the airflow
was dramatic. At the highest
airflow attainable in the combustion chamber, nearly 10 cm/sec
(a typical ventilation breeze), the
flames were bright and strong. As
airflow velocity decreased, the
flames became shorter but wider.
In addition, the flames became
less bright, and for P
polyethylene, they showed two
colors, a bright part decreasing in
volume and a nearly invisible
remainder (see the photographs).
Changes in flame appearance with airflow velocity for burning polyethylene rods in microgravity Airflow and flame spread
are from left to right in the photographs. (a) Air velocity, 8 5 cm/sec. (b) Air velociQ 4.0 cm/sec. (c) Air velocity, 2.0 crn/sec.
.
(d) Air velocity, 1.O cm/sec.
137
Finally, at a very low velocity, the flames extinguished. For the plastics
tested, this minimum velocity was very low, around 0.3 to 0.5 cm/sec.
This finding confirms that at least a slight airflow is required to maintain
a flame in microgravity for these types of materials.
The results of the project are significant for spacecraft fire safety. Of course,
the plastics studied are flammable, and their use is limited on spacecraft.
Because they are so common and difficult to replace, however, some
quantities of these materials will be present in cabins, even on the International Space Station. The encouraging result is that the practice of shutting
off ventilation or cooling airflows upon a fire indication or alarm will very
likely extinguish small fires. On the other hand, if the shutoff is slow, fires
may persist for some time under the stimulation of low airflows. The Mir
tests also showed that the nearly invisible flames observed under low airflows are still hot and, therefore, could ignite nearby objects.
Ivanov, A.V., et al.: Experimental
Verificatio [E-1b77a0f62becebf7]
- Fourth United States Microgravity Payload: One Year Report — recorded page 1 (physical PDF page unverified): m
on the door
unlatches
radiators
when
closed
[16].
and the deploy
are unlocked
the
motor
moves
and deploys
In deploying
the radiator
each
to the desired
position.
The
excitation
third
deployment
of the Orbiter
harmonics
deployment
are
excited.
of the port
illustrates
or stowage
of either the port
structural
modes.
In particular,
the impact
Figure
15 is an acceleration
side radiator.
of the radiator
The increased
deployment
On-board
Table
timeline.
times
14 shows
This
shifted
evidenced
case
was
by examining
Analyses
wake
that
stop times
around
the
versus
time
mark
150-second
plot
during
of this plot
sleep
sleep
duration
as dictated
time
hand,
wake-up
for
the
song
Cycle
of crew
progressed
start
other
magnitude
Sleep
scheduled
and OARE
SAMS
show
to sleep.
and
it, the
On the
a daily
magnitude
Activities---Crew
as the mission
has
vector
on the environment.
the nominal
nature
not instantaneous.
in this
start
that
in time
As human
certainly
from
the MET
shows
forward
constraints.
which
table
or starboard
side radiator
results
in a general
the 6.3 Hz structural
mode and its second and
sleep
sleep
an obvious
quieting
to quantify
was
from
the mission
replanned
eight
was
hours,
sleep
by landing
can
stop
and
be planned,
time
occurs
broadcast
can
below
this quieting,
up
Spartan
but
be enforced
about
to the
and
crew.
start
deployment
the
transition
with
is
an alarm,
data.
In an attempt
that
taken
13 Hz when
the RMS
acceleration
These
the crew
level
facts
are
transitions
contributed
by
the spectrum
below
13 Hz was calculated
approximately
009/12:00
to 013/12:00)
for SAMS TSH B on both Units
every 66 seconds
for a 96-hour
span (MET
F and G. Figure 16 shows the results of these
calculations
of consecutive
vertical
dashed/solid
for this 4-day
time frame.
Note
crew
for Unit
sleep
start/stop
F.
The
times,
four
pairs
respectively,
acceleration
levels typically lags scheduled
excitation
of the environment
is coincident
song.
For the plot shown
in Figure
lines
again
indicate
that actual
scheduled
reduction
in
sleep start times by at least several minutes,
while increased
with the scheduled
wake times owing to the daily wake-up
16, the mean
RMS
acceleration
during
the non-sleep
times
was 62
lagRM while the mean RMS acceleration
s,
during the four sleep periods
was 23 lagR_. Calculations
for
Unit G yield a mean
RMS acceleration
during
non-sleep
times of 55 lagm_s, and a mean
RMS
acceleration
during
As
another.
sleep
periods
of 29 Pgam"
might be expected,
the crew may have to wake during
a sleep period for one
It is quite possible that this is what happened
at around MET 003/17:20
when there
10 minutes of heightened
spectral response,
entry in the PIMS mission
logbook,
which
rotate
and
identification,
unsuccessful
disturbance
move"
it is merely
search
sources.
A summary
versus
periodic
at that
time format
quieting
time.
conjecture.
(by Marshall
plot
The
correlation
The IDGE
Space
of the OARE
in Figure
of the data
17.
particularly
notes that
Flight
data
team's
axes.
clearly
concern
is not
about
STS-87
illustrates
Peak-to-peak
197
here
and Johnson
for the entire
This figure
on all three
below 10 Hz. This period coincides
with an
the IDGE science
team observed
"their crystal
implied
Center
reason
or
were 5 to
a definitive
their crystal
Space
Center
mission
variations
motion
prompted
controllers)
is provided
the sleep cycles
cause-and-effect
in acceleration
of the crew
are on the order
an
for specific
through
the
of lxl0 6 g for
crew active periods
shown in [1] more
payloads
and 0.2x10 6 g for crew sleep periods.
clearly illustrate
that multiple
attitudes
and the non-microgravity
payloads,
On-board
While
other
crew
non-sleep
sleep
times
provides
a mission
Affair
a certain
that afford
quasi-steady
acceleration
plots
in support of separate
USMP-4
Spartan.
Activities---Public
clearly
during
including
Additional
were flown
Office
measure
similar
Events
of quieting
effects
as detailed
on the acceleration
earlier,
there
environment.
are
Most
notably,
Public Aff [E-6821163b1b183a5d]
- Fifth International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): 
non-steady
and
PMMA
state,
Delrin
drop.
destruction
flame
1
at V
of polyethylene
temperature
This
of the sample:
to = 70-80°C
d
for the Space
oxygen
The
longer
the flow
at Cox = 23%.
faster
oxygen
transport
'rl = 5 - 15
polyethylene,
ground
test,
in
Vii,,,
samples
in microgravity
were
=
still
(1:1< 13 sec)
on Vl_mand Xl indicate
the molecular
by forced
Station
at
Mum < 1 cm/sec.
low (Cox = 21%),
a fire in the Space
at
Cox =
in Skorost
quickly:
For
therefore
in
cm/sec
Vii m at
stopped
very
in the
All data obtained
is relatively
was
Polyethylene
was 23.5%,
but at
Vt_m = 3.4 cm/sec
('_1 = 30 sec).
to 0.3 - 0.5 cm/sec;
0:1 = 55 sec).
Vl_m = 0.55
apparatus,
happened
velo-
less than 0.3 cm/sec;
in microgravity,
when
that the fire extinguishes
observed
during
shape
for
all over the volume
of cases,
at
that, in
diffusion
convection
compartment
of the bubble
in the direction
the ejection
of the gaseous
products
combustion
were
and flame
polyethylene),
of melting
is
into com-
might
be exting-
in the Skorost
(almost
and
material.
intensive
The
with intensive
bubbles
happened
Those
apparatus
of spherical
(for
results
shape
for
Delrin
and
of measurements
the required
size
for
of 100 - 150 sec.
occurred
size of the gaseous
up to 4 - 5 cm in length.
experiment
on the sample
the size of the melt drop will not reach
in microgravity
burning,
the space
melt ball formation
for the time increment
Collapsing
tongues---ejected
Vnm was
be deter-
for limiting
on the ground
on the ground,
samples
concentration
Vlim-----can
Values
[1] obtained
PMMA
Again,
time was
close
concentration
growing
boiling
even
material.
Vl_m was
or of ellipsoidal
combustion
melting
Fig.
the flame-
at V = 10 cm/sec.
velocity
in the narrow-channel
of the PMMA
Therefore,
that for majority
the steady
molten
Delrin
For
at Co,`: = 23%.
gravity
phenomena
especially)
indicated
data.
in microgravity.
due to constantly
PMMA
convection
fire and the additional
by flow shutoff
The
were
on these
to 0.05 - 0.1 mm/sec
process.
than values
at Co× = 23%.
indicated
than in normal
uished
and the mater-
The flame-spread
the surface
mm,
in microgravity,
and Vl_m = 3.5 cm/sec
flow shutoff
zone
to be lower
the extinction
at Co,, = 25.4%,
The space
and the initial
for fire extinction
for Delrin
the extinction
in normal
8.5 cm/sec
rate along
5 = 0.375
collected.
flow V decreases,
flammability--limiting
was close to 0.5 cm/sec;
chamber,
microgravity
based
VF = 1.6 mm/sec
and
with the suppressed
0.45
=
Co,` = 21% and V_m = 2.4 cm/sec
sec, while
determined
were
size
if any, et cetera.
at V = 8.5 cm/sec
in the thickness
experiment,
and data
the flame
of concurrent
higher:
of material
apparatus
Vii
and 25.4%
combustion
were
that the flame-spread
and conditions
in microgravity
and
surface
0.5 - 0.75 mrn/sec
for the Skorost
convection.
Cox = 21%
to characterize
the velocity
was significantly
the test modes
suppressed
by computer,
[5].
The important
mined
When
by the difference
experiment
parameters
and the sample
In [5] it is shown
(0.375 mm thick)
was analyzed
destruction
V.
as well: from
= 4.5 mm, to = 20°C
Shuttle
the flame
of VF versus
= 0.3 - 0.5 cm/sec.
might
for various
rate of the material
shows
insulation
combustion
jets
opposite
of thermal
tongues
sometimes
with
were
to the flow.
destruction
inside
the foamy
was comparable
the ejection
burning
of different
boiling
PMMA
as well.
length
to the size of the
of the products
and looked
like
Jets
of thermal
the bright
combustion
and
drop of
of gaseous
brightness
zones
occurred
products
were
-
with
of
formed.
49
Polyethylene
combustion
the semitransparent
when
the flow
started
molten
velocity
to fluctuate
8.5 cm/sec,
drop,
was
with
wave
of the concurrent
candle flame
Shuttle.
the combustion
When
longitudinal
flame
(V = 8.5 cndsec).
formation
became
unstable:
were
was about
during stable
combustion
Glovebox
of this type
experiments
the flame
observed,
the measured
observed
Station
was
i.e. 100 higher
at the maximum
on Orbital
front
from
flow velocity
60 mm [E-667fe69b6ea2e598]
- Flammability Aspects of a Cotton-Fiberglass Fabric in Opposed and Concurrent Airflow in Microgravity — recorded page 1 (physical PDF page unverified): Flammability Aspects of a CottonFiberglass Fabric in Opposed and
Concurrent Airflow in Microgravity
Paul Ferkul, National Center for Space Exploration Research
Sandra Olson, NASA Glenn Research Center
Michael Johnston, Case Western Reserve University
James T’ien, Case Western Reserve University
This work was supported by the NASA Space Life and Physical Sciences
Research and Applications Division (SLPSRA).
Presented at the American Society for Gravitational and Space Research 2012 Annual Meeting
New Orleans, Louisiana
Science Background:
♦ Combustion of solid fuels in
microgravity has been an active area
of research
Typical Flammability Boundary for a Solid Fuel
0.23
0.22
0.21
♦ Numerical models predict that 1-g
buoyant flows profoundly affect fuel
flammability
0.20
Flammable
O2 Mole
Fraction 0.19
1-g buoyant
flow limit
0.18
♦ Microgravity experiments burning
thin fuels have verified this
prediction, but ground-based facilities
are too short to examine the burning
of thicker fuels
♦ Flow in range < 30 cm/s is of interest
0.17
0.16
Not Flammable
0.15
1
10
Flow speed (cm/s)
100
300
Hypotheses:
♦ Materials in microgravity, with
adequate ventilation, may burn more
readily compared to normal gravity
with other conditions being identical
(pressure, oxygen concentration,
temperature, etc.)
♦ Testing at constant O2 mole fraction
permits studying flame spread and
extinction at low and high flow speed.
Typical Flammability Boundary for a Solid Fuel
0.23
0.22
0.21
0.20
Flammable
O2 Mole
Fraction 0.19
1-g buoyant
flow limit
0.18
0.17
0.16
Not Flammable
0.15
1
10
Flow speed (cm/s)
100
Approach:
♦ Microgravity combustion tests were performed
aboard the International Space Station using the
BASS (Burning and Suppression of Solids)
hardware.
♦ The wind tunnel was installed in the Microgravity
Science Glovebox which supplied power, imaging,
and a level of containment.
♦ Cotton-fiberglass blend fabric samples were
mounted inside a small wind tunnel which could
impose airflow speeds up to 40 cm/s.
♦ The effects of airflow speed on flame appearance,
flame growth, and spread rates were determined
in both the opposed and concurrent flow
configuration.
Science Applications:
 Understanding of long-duration microgravity solid material burning and extinction
 Improved strategies for NASA spacecraft materials selection; link actual burn
behavior in microgravity to Earth-based selection methods
 Improved combustion computational models used in the design of fire detection
and suppression systems in microgravity and on Earth
 Validated detailed combustion models in the simpler flow environment of
microgravity build more complex combustion models needed to capture the
important details of flames burning in normal gravity; models have wide
applicability to the general understanding of many terrestrial combustion
problems.
Microgravity Science
Glovebox (MSG)
BASS flame visible
through viewport
Fish-eye view of the inside of the Microgravity Science Glovebox (MSG)
Hardware Details
Top window
Permits variety of solid samples to be mounted, ignited, and burned:
Thin, flat (17)
Spheres (12)
Thick, flat (4)
(Note: samples are not to scale; samples can be flipped 180 degrees if desired)
Candles (8)
Experiment Operation:
Flow Duct
Airflow
Top Window and
Sample Holder
Experiment Operation:
Fuel Sample Installed
Airflow
Experiment Operation:
Igniter On
Airflow
Experiment Operation:
Flame
Airflow
Experiment Operation:
Flame Spread
Airflow
Experiment Operation:
Flame Responds
to Higher Flow
Airflow
Changes
Experiment Operation:
Flame Extinction
(Flow reduced too far
or fuel consumed)
Airflow
Hardware Summary:
Sample Images
 BASS utilized the on-orbit SPICE hardware;
minor modifications were made to burn solid
samples
Digital Still
Video
 Small flow tunnel
 Solid samples were installed, ignited,
extinguished, and recorded
 Video and digital still camera provided bulk
of the data. Flame appearance, behavior,
spread rate, and extinction dynamics were
measured
 Ai [E-ca4ca79d1757f8e5]
- The 3rd International Microgravity Combustion Workshop — recorded page 1 (physical PDF page unverified): study of this very low speed flow is whether the flame is followed
by slight flow control. Figure 5 shows that there was little difference between the
equivalence ratio controlled arbitrarily and the flame interval.
Figure 6 is a plot of the equivalence ratio and the distance between twin flames
versus time. In the case of methane, the twin flames approached monotonously and
were extinguished after they becoming united. This proved to be true as expected.
In the case of propane, however, twin flames were united and extinguished as well,
although it was expected that extinction would occur when the flames were still
separate, owing to the Lewis number effect.
Since sudden changes of the flame interval were always recognized in the case of
propane, the location of the symbol (*) in Fig.6(b) was defined as the point of
flammability limit. This is because, after this point, flames cannot maintain their
self-propagation characteristics and only unstable flames can exist. The variation
of the nominal stretch rate with the equivalence ratio at extinction showed that the
flammability limit of the propane/air mixture was 0.50.
Blowoff Limit (PI: J. Sato)
The flow velocity gradient at the burner rim has a great effect on the blowoff condition of premixed flames. When the flow velocity of the mixture is small, however,
the effect of buoyancy may also be significant, and so it is expected that there is a
discrepancy between the case for that in normal gravity and for that in microgravity
for a very lean or a very rich mixture. This experiment is now being conducted using
methane as a fuel.
428
Diffusion Flame (PI: J. Sato)
Methane is issued from a tube with an inner diameter of 5 mm, and an airflow
nozzle with a diameter of 54 rom is constructed in a concentric configuration. The
thickness of the fuel burner rim is 0.1 mm to avoid the effect of turbulence at the
rim. In normal gravity, flickering of the diffusion flame with a frequency of about 10
Hz was observed at a fuel velocity of 25.5 cm/s when the outer airflow is stopped.
Switching from this condition in normal gravity (Fig.7(a» to the same condition
in microgravity, the flame shape changed as shown in Fig.7(b), (c) and (d), in that
order, within one second. Since air is not supplied by natural airflow convection and
is transferred only by diffusion, the flame becomes weak and only blue flame exists
around the burner port, as shown in Fig.7(d). It can be seen in Fig.7(d) that the
diffusion flame developed below the burner port owing to the downward diffusion of
methane.
In the present study, only the diffusion flame was observed, but in the next step, the
turbulent flame will be observed to determine the contribution of natural convection
to the turbulent diffusion flame. In addition, we plan to study the effect of air
temperature on the diffusion flame.
The Effect of Magnetic Field (PI: K. Ito)
Oxygen molecules are paramagnetic, and therefore the transport of oxygen should
be influenced by a magnetic field. The objectives are not only to investigate the
combustion mechanism in a magnetic field but also to promote combustion, for
example, by utilizing the change of the flame shape.
A butane diffusion flame was established on a circular tube with an inner diameter
of 0.6 cm. The tube was made of copper so as to be independent of magnetic field.
Figure 8 shows the arrangement of the burner, the flame(R) and the magnet (A),
the magnetic force (H) of which had a certain distribution. Butane was chosen as
the fuel.
.
A comparison of the flame shapes is shown in Fig. 9. Standardizing flame (A) in
normal gravity and without magnetic field, totally, flames (B, C) without magnetic
field changed more drastically, while flames (A', B', C') with magnetic field did not
change much. Actually, it was not possible to establish a flame in microgravity (C),
although it was possible to sustain a flame if the field was magnetized (C'). This
means that the effect of the magnetic field on oxygen transpo [E-46e240439315046d]
- Burning and Suppression of Solids–II  (BASS-II) Summary Report — recorded page 1 (physical PDF page unverified): ysis in future.
5.2 Introduction
The NASA Burning and Suppression of Solids—II (BASS–II) tests examine the combustion of
different solid materials and geometries in microgravity. While flames in microgravity are driven by
diffusion and weak advection due to ventilation systems and crew movement, the current NASA
spacecraft material selection test method (NASA–STD–6001 Test 1) (Ref. 1) is driven by buoyant forces
since gravity is present. So, the BASS–II results will be used in comparison with ground-based
experimental setups aimed at replacing NASA’s current test method for screening materials used onboard
spacecraft. The data gathered will also help us understand and know more about behavior of fires in space
so that space travel can be made safer in the future. The BASS–II experiments have provided us with an
extensive thick fuel microgravity database that did not exist previously. Previously, thick-fuel true
microgravity data was obtained by Olson and others in a study involving Sounding Rocket experiments
(Ref. 2). The study comprised a series of combustion experiments on polymethylmethacrylate (PMMA) at
very low velocity opposed flow and external radiant flux.
The institutions taking part in BASS–II operations are Case Western Reserve University; University
of California, Berkeley; NASA Glenn Research Center; San Diego State University; and Michigan State
University (Ref. 3). There are three categories of samples: flat samples, rod samples, and a section of a
large solid sphere. The flat sample materials will include acrylic films and sheets of different thicknesses,
and a cotton-fiberglass fabric blend Solid Inflammability Boundary at Low-Speeds (SIBAL) fuel. The rod
samples are made of black or clear acrylic and will provide solid fuel regression rates and extinction
limits for both opposed and concurrent flow. The large solid spherical section, also made of acrylic, will
be used to study ignition of thick materials and flame growth over the thick material.
NASA/TM-20210011385 56
5.3 Experimental Setup and Summary
The BASS–II hardware shown in Figure 5.1 comprises a small flow duct with an igniter and a small
nozzle along with exchangeable fuel samples. The BASS–II flow duct is placed inside the Microgravity
Science Glovebox (MSG) (255 L) (Ref. 5) onboard the International Space Station (ISS). A radiometer
placed at the top measures the intensity of the flame. A fan is used to produce forced flow of air in the
duct. Also present is an anemometer that measures the velocity of air entering into the duct. A Nikon
digital camera (Nikon Corporation) looks through the top of the flow duct normal to the sample surface
and a high-definition video camera uses a mirror to look through the front door of the duct at the edge of
the flat sample (orthogonal to the high-definition camera). A total of 20 PMMA flat samples were burnt
during the BASS–II experimentation (Table 5.1). The sample thickness varied from 1 to 5 mm thick. The
samples burnt were all either 1 or 2 cm wide. All the burns are either one sided or two sided. The airflow
was always opposed. Airflow speeds ranging from as low as 3 cm/s up to 20 cm/s were used in the flow
duct.
Prior to the start of testing at each session, a crew member installs the hardware in the MSG. The fan
calibration is set before the flame is ignited. Once ignited, the flame is allowed to stabilize at first and
then the airflow is adjusted throughout the test. Fan speed, radiometer reading, and the time is monitored
during the entire test. The airflow is turned off after the test. Videos and data are downlinked to Earth
(Ref. 3). The still images and videos from the data are tracked using Spotlight–16 (NASA image tracking
software) (Ref. 6). Data are then imported to Excel® (Microsoft®) to obtain flame spread rates. A graph of
the position versus time for one of the tests is found in Figure 5.2. The black line in the plot represents the
O2 concentration profile during the duration of the test. A  [E-5212a18ab5fb37c1]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Approach; https://ntrs.nasa.gov/citations/20160000593 [E-context-5227141f2aaa7feb2e37]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-3b27486ede2bf8151a2f]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-80d7fc00aae08504c315]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-e6623c40985279bec3b2]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, PMMA rod comparison; https://ntrs.nasa.gov/citations/20160000593 [E-context-d0e9f6c262d92e57e3bd]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Material Ignition and Suppression Test; https://ntrs.nasa.gov/citations/20160000593 [E-context-87d3a70a788ae398fe4a]
- Spacecraft Fire Safety Needs for Exploration — ntrs-20205007829, PDF page 16, table None, row None; https://ntrs.nasa.gov/api/citations/20205007829/downloads/Exploration%20Needs%20in%20Fire%20Safety_9-25-2020.pdf [E-context-d1e50788b120206316a0]
- Flammability Aspects of a Cotton-Fiberglass Fabric in Opposed and Concurrent Airflow in Microgravity — ntrs-20130012832, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20130012832 [E-1bc76d1f2a957fd8]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-1a048dade39a6ea2]
- Research and Technology 1999 — ntrs-20000056096, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20000056096 [E-1b77a0f62becebf7]
- Fourth United States Microgravity Payload: One Year Report — ntrs-20000010691, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20000010691 [E-6821163b1b183a5d]
- Fifth International Microgravity Combustion Workshop — ntrs-19990053965, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19990053965 [E-667fe69b6ea2e598]
- Flammability Aspects of a Cotton-Fiberglass Fabric in Opposed and Concurrent Airflow in Microgravity — ntrs-20130012832, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20130012832 [E-ca4ca79d1757f8e5]
- The 3rd International Microgravity Combustion Workshop — ntrs-19960008386, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19960008386 [E-46e240439315046d]
- Burning and Suppression of Solids–II  (BASS-II) Summary Report — ntrs-20210011385, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20210011385 [E-5212a18ab5fb37c1]
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Residence Time Driven Flame Spread; https://ntrs.nasa.gov/citations/20160000593 [E-context-90f697823c2ba1b2ea82]



## What observations distinguish normal gravity and microgravity silicone tests?

QueryIntentV2 constraints: `[{"relation": "hasMaterial", "entity_id": "context:silicone-material"}, {"relation": "hasGravityCondition", "entity_id": "microgravity"}]`; requested classes: `['ReportedObservation']`. Effective gravity policy: `{'enabled': True, 'explicit_values': ['microgravity'], 'comparative': True, 'default_preference': [], 'preference_relation': 'hasGravityCondition', 'authority': 'retrieval_preference_only'}`.

DIRECT: ['context:silicone-flight-observation', 'context:silicone-ground-observation']. RELATED: ['context:silicone-ground-observation', 'context:silicone-flight-observation']. Native resolver invoked; source/group paths retained in the companion receipt.

## Answer
Source-backed evidence matching the validated constraints is listed below.
Results are grouped by each requested concept; these groups do not establish a single experiment satisfying all concepts simultaneously.

## Applicable scientific context

- gravity: normal-gravity; applies to context:silicone-ground-observation. The group statement and verified membership establish applicability [E-context-a79df97c23d629116824].
- material: context:silicone-material; applies to context:silicone-ground-observation. The group statement and verified membership establish applicability [E-context-a79df97c23d629116824].
- gravity: microgravity; applies to context:silicone-flight-observation, context:silicone-ground-observation. The group statement and verified membership establish applicability [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b].
  Exceptions: context:silicone-ground-observation
- material: context:silicone-material; applies to context:silicone-flight-observation. The group statement and verified membership establish applicability [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b].

## Direct evidence

- context:silicone-flight-observation (requested group: microgravity) [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]
  Matches: ['hasMaterial=context:silicone-material', 'hasGravityCondition=microgravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: context:silicone-material; actual: ['context:silicone-material'].
  hasGravityCondition: MATCH; requested: microgravity; actual: ['microgravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:silicone-ground-observation (requested group: normal-gravity) [E-context-a79df97c23d629116824]
  Matches: ['hasMaterial=context:silicone-material', 'hasGravityCondition=normal-gravity', 'reviewed requested information class']; differs: []; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: context:silicone-material; actual: ['context:silicone-material'].
  hasGravityCondition: MATCH; requested: normal-gravity; actual: ['normal-gravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
Related evidence: 2 condition groups representing 2 candidates. All candidate IDs and citations remain available in the evidence bundle.

## Related evidence

- context:silicone-ground-observation (requested group: microgravity) [E-context-a79df97c23d629116824]
  Matches: ['hasMaterial=context:silicone-material', 'reviewed requested information class']; differs: ['hasGravityCondition=microgravity']; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: context:silicone-material; actual: ['context:silicone-material'].
  hasGravityCondition: DIFFER; requested: microgravity; actual: ['normal-gravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.
- context:silicone-flight-observation (requested group: normal-gravity) [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]
  Matches: ['hasMaterial=context:silicone-material', 'reviewed requested information class']; differs: ['hasGravityCondition=normal-gravity']; unknown: []; invalid: [].
  hasMaterial: MATCH; requested: context:silicone-material; actual: ['context:silicone-material'].
  hasGravityCondition: DIFFER; requested: normal-gravity; actual: ['microgravity'].
  Findings cannot be transferred across materials or conditions; category matches do not establish uniform family behavior.

## Reported observations

- Results were convincing although rather anticlimactic as none of the silicone samples burned.
When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly
extinguished. The igniters all appeared to function normally and the materials were clearly damaged in
the vicinities of the igniters. (requested group: microgravity) [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]
  Statement applicability — hasMaterial: MATCH; requested: context:silicone-material; established: ['context:silicone-material'].
  Statement applicability — hasGravityCondition: MATCH; requested: microgravity; established: ['microgravity'].
  Topical statement selection does not establish every requested experimental condition
- In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.

In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn. (requested group: microgravity) [E-context-a79df97c23d629116824]
  Statement applicability — hasMaterial: MATCH; requested: context:silicone-material; established: ['context:silicone-material'].
  Statement applicability — hasGravityCondition: DIFFER; requested: microgravity; established: ['normal-gravity'].
  Topical statement selection does not establish every requested experimental condition
- Results were convincing although rather anticlimactic as none of the silicone samples burned.
When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly
extinguished. The igniters all appeared to function normally and the materials were clearly damaged in
the vicinities of the igniters. (requested group: normal-gravity) [E-context-d86d030e275ce04b8b82, E-context-ec300b3756c4bd69021b]
  Statement applicability — hasMaterial: MATCH; requested: context:silicone-material; established: ['context:silicone-material'].
  Statement applicability — hasGravityCondition: DIFFER; requested: normal-gravity; established: ['microgravity'].
  Topical statement selection does not establish every requested experimental condition
- In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.

In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn. (requested group: normal-gravity) [E-context-a79df97c23d629116824]
  Statement applicability — hasMaterial: MATCH; requested: context:silicone-material; established: ['context:silicone-material'].
  Statement applicability — hasGravityCondition: MATCH; requested: normal-gravity; established: ['normal-gravity'].
  Topical statement selection does not establish every requested experimental condition

## Contextual source quotations

These documentary passages do not establish the requested experimental constraints.
- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — Approach: Approach
― Microgravity combustion tests were performed aboard the International Space Station.
Active crew support for real-time “lab partner” operations.

― The wind tunnel was installed in the Microgravity Science Glovebox which supplied power,
imaging, and a level of containment.
― Fuel samples were mounted inside a small wind tunnel which could impose airflow speeds
up to 40 cm/s.

― Main variables are airflow speed and oxygen concentration (oxygen varied below 21% by
adding nitrogen).
― Flame appearance, flame growth, and spread rates were determined in both the opposed
and concurrent flow. [E-context-5227141f2aaa7feb2e37]
- Results of Large-Scale Spacecraft Flammability Tests — Summary and Conclusions: Summary and Conclusions
• For the first time, a large-scale fire was intentionally set inside a spacecraft while in orbit.
• In addition, smaller samples of various materials were burned in a subsequent spaceflight.
• Unlike 1-g, the results revealed that a steady flame could be achieved even for a wide sample burning in concurrent-flow.
• The flames spread more slowly than prior tests in smaller ducts. This behavior of the flame demonstrated the importance of
confined spaces for potential spacecraft fires.
• Flammability of silicone in microgravity appears to be reduced compared to normal gravity, at least for the flow speeds tested.
• Nomex®, a common material used on the ISS and rated “safe,” could not be ignited even when bathed by a pilot flame.
There are plans for the Saffire project to continue with additional experiments examining the effects of enhanced oxygen at
reduced pressure.
Results will increase our knowledge of how a fire spreads in a large enclosure, and what effects the fire has on the spacecraft.
This understanding will influence vehicle design and materials screening, ultimately increasing the safety of the crew. [E-context-4679bc2d5e96d1425335]
- Results of Large-Scale Spacecraft Flammability Tests — recorded page 1 (physical PDF page unverified): he vehicle was guided for destructive re-entry into the Earth’s atmosphere.
5
Air Flow
29 cm
5 cm
The Saffire flow duct (18” x 20”). Two cameras and four
radiometers are indicated. Camera and radiometer fields of
view are shown by the cones, shaded blue and red, respectively.
Saffire-II sample card with the
nine samples, and ignition
locations are indicated in red.
There were six sample thermocouples per flight.
7
Configurations
Saffire 1
Saffire 2 (samples 5 cm wide)
Silicone
Ignition power:
Saffire 1: 165 W (for 8 s); 4.1 W/cm (per unit fuel width)
Saffire 2, all samples except thick PMMA:
SIBAL fabric
80 W (for 9.2 s); 16 W/cm (per unit fuel width)
Saffire 2, thick PMMA:
97 W (for 30 s); 19.5 W/cm (per unit fuel width)
Thin PMMA/Nomex®
SIBAL fabric
40.6 cm wide
Thick PMMA
Average flame power:
Saffire 1: 1200 +/- 300 W
Saffire 2: (SIBAL fabric) 200 +/- 50 W
Saffire 2: (Thick PMMA) 600 +/- 100 W
Saffire-2 Description
2-1
2-2
2-3
2-4
Nine samples; 5 cm wide by 29 cm long
20 cm/s flow for all tests except for Sample 2-6 (25 cm/s)
All upward burns except Sample 2-4 was downward
Initial oxygen concentration 22.1% (ISS reading,
slightly higher than Saffire-1’s 21.7%)
2-5
2-6
2-7
2-8
2-9
Samples 2-1 to 2-4 were silicone sheets 0.27, 0.61, 1.03, and 0.37 mm thick.
Samples 2-5 and 2-6 were cotton-fiberglass fabric identical to that used in Saffire-1.
Sample 2-7 had a composite construction, the first 5 cm of which was a thin (0.8 mm)
sheet of PMMA and the remainder Nomex® fabric (HT 90-40).
Samples 2-8* and 2-9* were PMMA slabs with a nominal thickness of 1 cm. Sample
2-8 had some surface features, including a groove down the center (in the flow
direction) on both sides, while Sample 2-9 was flat.
* Results from these samples are described in another paper at this conference.
9
Saffire-2 Description (con’t)
2-1
2-2
2-3
2-4
2-5
2-6
2-7
2-8
2-9
Thick PMMA Sample cross sections:
The middle 1.8-cm-wide portion of Sample 2-8 is
only 0.4 cm thick.
The ignition energy and time for samples 2-1 through 2-7 were chosen to mimic the
NASA 6001 Test 1 ignition, 736 J applied uniformly for 9.2 s.
Samples 2-8 and 2-9 had slightly more powerful igniters (97 W instead of 80 W) and
were left on longer (30 s instead of 9.2 s) to assure ignition of these thick fuels.
10
Saffire-2; Why Silicone?
Upward burning silicone samples (2-1 to 2-3) were 0.27, 0.61, and 1.03 mm thick.
In upward-burning, normal-gravity tests, these three thicknesses spanned the flammability limits from
significant burn, to partial burn, to no burn.
‒ The 0.27-mm thick samples were almost always completely consumed
‒ The 0.61-mm thickness burned on average 7.6 cm of the available 30 cm before extinguishing
‒ The 1.03-mm thickness would not burn at all.
Downward burning silicone sample (2-4) was 0.37 mm thick.
In downward burning, normal gravity tests, this thickness was completely consumed. The next higher
thickness tested (0.61 mm) would not burn.
Microgravity behavior was sought:
‒ How much of the available fuel would be burned?
‒ Would microgravity prove more or less favorable to flame spread?
11
Saffire-2; Silicone Results
Results were convincing although rather anticlimactic as none of the silicone samples burned.
When the igniter was powered off, a tiny gas phase flame remained but did not spread and quickly
extinguished. The igniters all appeared to function normally and the materials were clearly damaged in
the vicinities of the igniters.
It was surprising that not even the thin sample could permit any flame spread, given that it was entirely
consumed in normal gravity. Previous experience with cellulosic fuels (paper and fabric) and even
PMMA suggested that if a flame could persist in upward 1-g tests then it would also burn in
microgravity at a moderate flow speed which was less than that typical in buoyant flow.
12
Saffire-2; Silicone Results (con’t)
The behavior of silicone in microgravity is perplexing perhaps due to its complex burning:
‒ Silicone produces fine silica  [E-49fde889c36ce643]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — recorded page 1 (physical PDF page unverified): tes in quiescent and very-low-speed flows were measured with the
WIF experiment for comparison with tests in normal-gravity buoyant environments.
1. EXPERIMENTAL OBJECTIVES
The Wire Insulation Flammability Experiment (WIF) was designed to obtain test data on two
related phenomena:
632
(1)
Observe and measure the joule heating of electrical wire in a quiescent, then low-speed
forced-flow environments, for comparison with normal-gravity behavior and with
established tests for rating spacecraft electrical systems.
(2)
Observe and measure the ignition and spreading of a flame over the insulation of
overheated electrical wire in very-low-speed flows in microgravity. Distinguish between
flames spreading in concurrent and opposed flow, and compare with flame spreading in
normal gravity.
To obtain these desired observations, four experiments were conceived, two each in concurrent
and opposed flows.
II. EXPERIMENT HARDWARE
Four nearly-identical WIF test modules, designated WIF-A,B,C, and D (see figure 1) were built
for the STS-50 mission. The modules were designed to function inside the Glovebox Experiment Facility
(GBX) which provided electrical power, flowing air, and photographic capability.
Each module consisted of a combustion chamber (see figure 2) open at both ends, configured as
a miniature wind tunnel. At one end a flexible duct was provided for connection to the GBX air
circulation system, the air supply for the experiment. A small bending flag anemometer, made from the
jewel-bearing movement of an electrical meter, was positioned in the tunnel to indicate the airflow
velocity. A metal screen covered the exit port to cool the gases exiting the WIF module and to contain
any particulates released during combustion.
A single insulated wire sample, 1.5 mm diameter, 110 mm long, was mounted axially in the duct,
parallel to the aimow direction. The sample consisted of polyethylene insulation extruded onto a 0.75
mm nichrome wire core. The sample was connected to circuitry design to provide current for joule
heating the nichrome core. At
one end of the sample, a kanthol igniter wire was wound around the
insulation. In two modules, the ignitor was located near the flow exit so that the flame spread direction
would be opposed to the airflow direction; in the others, the ignitor was located near the entrance for
concurrent-flow flame spreading.
The electrical power deposited in the test wire cores via joule heating was controlled by
calibrated ballast resistors. The power deposition in the WIF modules A D were 1.27, 1.49, 1.59, and
1.75 watts, respectively. The resistances were selected to achieve different steady temperatures in the
wire samples near the melting point of the insulation, based on tests in a vacuum in normal gravity.
Four Type K, 0.07 mm wire diameter thermocouples were placed inside the sample to measure
wire temperatures and insulation temperatures near, but below, the surface.
Two additional
thermocouples were located in the gas phase, 2.5 mm and 1.5 mm from the insulation SUrfaCe, to
633
measure the flame temperatures. A window in the tunnel was framed by six thermocouple-temperature
displays (see figure 2). This window configuration was designed to allow simultaneous imaging of the
flame and the thermocouple displays using the glovebox video.
A second window in the tunnel
presented an orthogonal perspective used for 35 mm still photographs.
Two 10 cc vacuum bottles, located behind the combustion chamber, were connected through a
solenoid valve to smalldiameter metal sampling tubes, that terminated near the wire sample. The
vacuum bottles were designed for collecting gaseous samples of the off-gassing and combustion
products for post-flight chemical analysis. Two transmission electron microscope grids, approximately 3
mm in diameter, were attached to each exit screen for post-flight analysis of any captured particles.
The crew controlled the WIF modules using a small control box outside the GBX. The controlled
funct [E-d272290480488dc5]
- Results of Large-Scale Spacecraft Flammability Tests — recorded page 1 (physical PDF page unverified): ions
• For the first time, a large-scale fire was intentionally set inside a spacecraft while in orbit.
• In addition, smaller samples of various materials were burned in a subsequent spaceflight.
• Unlike 1-g, the results revealed that a steady flame could be achieved even for a wide sample burning in concurrent-flow.
• The flames spread more slowly than prior tests in smaller ducts. This behavior of the flame demonstrated the importance of
confined spaces for potential spacecraft fires.
• Flammability of silicone in microgravity appears to be reduced compared to normal gravity, at least for the flow speeds tested.
• Nomex®, a common material used on the ISS and rated “safe,” could not be ignited even when bathed by a pilot flame.
There are plans for the Saffire project to continue with additional experiments examining the effects of enhanced oxygen at
reduced pressure.
Results will increase our knowledge of how a fire spreads in a large enclosure, and what effects the fire has on the spacecraft.
This understanding will influence vehicle design and materials screening, ultimately increasing the safety of the crew.
26
27
Backup slides
28
Table I. Summary of Samples, Test Conditions, and Selected Results
Sample
Material
Width
Thickness
Length
1-1
Cotton-Fiberglass
40.6 cm
0.37 mm
94 cm
1-2
Cotton-Fiberglass
40.6 cm
0.37 mm
~ 10 cm
2-1
Silicone
5 cm
0.27 mm
29 cm
2-2
Silicone
5 cm
0.61 mm
29 cm
2-3
Silicone
5 cm
1.03 mm
29 cm
2-4
Silicone
5 cm
0.37 mm
29 cm
2-5
Cotton-Fiberglass
5 cm
0.37 mm
29 cm
2-6
Cotton-Fiberglass
5 cm
0.37 mm
29 cm
2-7
PMMA & Nomex
5 cm
0.85 & 0.37 mm 5 & 24 cm
2-8
PMMA
5 cm
See Fig. 5
29 cm
2-9
PMMA
5 cm
1 cm
29 cm
… Table I (continued)
Ignition
µ-g Burn
Sample Ignition Power
Burn Duration
Time
Length
1-1
182 W
8s
420 s
~ 84 cm
1-2
182 W
8s
70 s
~ 10 cm
2-1
80 W
9.2 s
Insignificant
~0
2-2
80 W
9.2 s
Insignificant
~0
2-3
80 W
9.2 s
Insignificant
~0
2-4
80 W
9.2 s
Insignificant
~0
2-5
80 W
9.2 s
145 s
29 cm
2-6
80 W
9.2 s
115 s
29 cm
2-7
80 W
9.2 s
140 s
5 cm & 0 ii
2-8
97 W
30 s
600 s
~ 10 cm iii
2-9
97 W
30 s
900 s
~ 10 cm iii
Flow
20 cm/s
20 cm/s
20 cm/s
20 cm/s
20 cm/s
20 cm/s
20 cm/s
25 cm/s
20 cm/s
20 cm/s
20 cm/s
µ-g Spread
Rate
1.8 mm/s
1.3 mm/s
n/a
n/a
n/a
n/a
2.1 mm/s
2.6 mm/s
n/a (Nomex)
Note (iv)
Note (iv)
Direction
Concurrent
Opposed
Concurrent
Concurrent
Concurrent
Opposed
Concurrent
Concurrent
Concurrent
Concurrent
Concurrent
1-g Burn
Length
Complete
~0
~ Complete
7.6 cm
~0
Complete
Complete
Complete
~ 0 (Nomex)
Complete
Complete
Δ %O2 i
21.7 to 21.5
~ 21.5
~ 22.1
~ 22.1
~ 22.1
~ 22.1
~ 22.1
~ 22.1
~ 22.1
22.1 to 22.0
22.0 to 21.9
1-g Spread Rate
Acceleratory
n/a
Acceleratory
1.2 mm/s
n/a
0.6 mm/s
Acceleratory
Acceleratory
n/a (Nomex)
Acceleratory
Acceleratory
i
Derived from measured CO2 production and referenced to initial O2 concentration reported by ISS.
The PMMA portion was completely consumed but the Nomex was not ignited.
iii This is the length of fuel with significant visible damage.
iv The flames remain anchored at the base of the sample which has a very slow regression rate (0.01 to 0.04 mm/s).
ii
29
30
31
32
33
34
35
36 [E-7ab386873c223183]
- Microgravity smoldering combustion on the USML-1 Space Shuttle mission — recorded page 1 (physical PDF page unverified):  peak temperatures
were greater in microgravity
than
normal gravity for all four thermocouples,
with the difference increasing
with distance from the igniter. The
temperature difference is presumably due to buoyant cooling in normal gravity, which would be most strongly felt
20
near the surface of the foam.These temperature histories can be used to roughly calculate smolder propagation
velocities using the method previously developed for ground-hased experiments [4]. Using that technique, it is
found that for all tests, the smolder was not steady but decayed from approximately 0.08 mm/s to 0.02 mm/s, and
finally extinguished. The smolder propagation velocities obtained for the normal-gravity tests experiments are also
similar. The calculated smolder velocities are of the same order of magnitude as those measured in larger
experiments of opposed-flow
smolder at low flow velocities (0.5 mm/sec) and natural convection smolder [8].
They correspond
to the "weak" smolder cases tested. The maximum
smolder velocities
measured
in those
experiments were obtained for flow velocities of 3 mm/sec and were of the order of 0.15 ram/see.
Char Patterns:
During the testing, the smoldering
foam was observed
to expand
and smoke, much of which later
condensed as a yellow residue on the module interior. Upon removal after testing, the samples were cut open to
reveal the extent of the smolder propagation.The
char pattern from normal-gravity
tests were found to be similar
to the pattern from the microgravity
test. The visible extent of propagation
was similar in both tests, but there
were two notable
differences. First, large voids, on the order of 1 em long, were created in the normal-gravity
char region, whereas there were none apparent in the microgravity char. The voids were found in other, but not
all, of the normal-gravity
tests and none of the microgravity tests.
It is speculated that the voids result from
gravitational
forces on the weakened polymeric structure, but it is not clear what controls their occurrence.
A
close comparison
of the char structure of the microgravity
and normal-gravity
tests also shows significant
differences.
The normal-gravity
voids had a crust of melted material which appeared to clog the foam pores.
Microscopic
observation of the normal-gravity
char showed that discolored filaments in some cases had melted
into spheres. Furthermore,
strong signs of fuel pyrolysis could also be observed at the edges of the char region.
These observations
are typical of a low temperature
smolder process [3,4]. In contrast, the char in the
microgravity
samples was more typical of high temperature smolder with a fibrous, relatively dense structure,
despite the similar temperature profiles.
Gas Analyses:
The results
of the analyses
of the post-combustion
gases
are presented
in Table
I, for the
microgravity and normal-gravity
tests. Only the major components have been included in the table. The results
are based on analyses,
performed
at the Toxicology
Laboratory
at NASA
Johnson,
with both Gas
Chromatography
(GC) and Gas Oammatography/lVlass
Spectrometry (GC/MS).
Oxygen depletion and
production of carbon dioxide, carbon monoxide, and hydrocarbon species are good indicators of the combustion
reaction characteristics. However, in interpreting the data, it should be kept in mind that smoldering is a lowtemperature
surface reaction that is generally oxygen limited. It is seen that the microgravity
smolder tests
produced significant amounts of carbon monoxide and carbon dioxide, as well as a number of light organic
compounds.
These species are characteristic of pyrolysis and oxygen-limited combustion.
It is believed that the
chlorinated compounds are contaminants resulting from the methylene chloride that was used to solvent bond flae
joints in the polycarbonate
modules. The normal-gravity
tests produced these species in substantially
smaller
amounts than the microgravity
tests. This is somewhat surprising,
since the extent of smolder propagat [E-1f2be6f603bde68c]
- Evaluation of Low-Gravity Smoke Particulate for Spacecraft Fire Detection — recorded page 1 (physical PDF page unverified): 61
0.258
0.398
0.465
0.619
0.170
0.232
0.384
0.539
2.154
1.872
2.312
1.834
2.530
2.108
2.198
2.442
2.211
1.892
Unaged
Kapton
Aged 720 s
Unaged
Lampwick
Aged 720 s
Unaged
Silicone
Aged 720 s
Unaged
Teflon
Aged 720 s
Unaged
Pyrell
Aged 720 s
Table 1: Diameter results for baseline runs for each material (Diameters are in micrometers).
The increased residence time afforded in the higher concentration zone at lower air speeds is expected to increase
the particle size. This is supported by figure 7which presents the diameter of average mass for all materials versus duct
velocity. This figure shows a strong trend of increased particle size at low flow rates with the greatest increase for the
Kapton smoke. This indicates that smoke trapped in an avionics enclosure or in poorly ventilated region can be expected
to be substantially larger than smoke released in well ventilated areas. In the most poorly ventilated areas (e.g. avionics
enclosures with no cooling air) the smoke can be retained at a relatively high concentration until it escapes. This effect
was simulated by varying the aging time over 30 to 2000 seconds in the SAME apparatus. The diameter of average mass
is plotted against the aging time in figure 8. The diameter is seen to consistently increase with aging time. This effect
can be substantial, producing an increase in the diameter from 55 to 100%. More discussion of this effect is presented
below with the TEM images.
Dust Track 10 micron/ 1 micron impactor mass ratio
DustTrak Ration (10 micron mass / 1 micorn mass)
2.50
2.00
Kapton unaged
1.50
Lampwick unaged
Teflon unaged
Silicone unaged
Kapton Aged
1.00
Lampwick Aged
Teflon aged
Silicone Aged
0.50
0.00
0.0000
0.1000
0.2000
0.3000
0.4000
0.5000
0.6000
0.7000
Diameter of average mass (µm)
Figure 6: Plot of the ratio of the mass concentration from the DustTrak with a 10 micron impactor
to the Dust Trak with a 1 micron impactor for different materials, flow rates and sample
temperatures and unaged conditions
8
Diameter of Average Mass versus Air Speed fixed temp unaged
1.40
Diameter of averagef mass (µm)
1.20
1.00
0.80
Teflon
Pyrell
Silicone
0.60
Lampwick
Kapton
0.40
0.20
0.00
0
2
4
6
Air Flow (cm/s)
8
10
Figure 7 Diameter of average mass versus air flow for different materials. These tests were conducted at a constant
temperature for each material with no aging.
0.80
0.70
0.60
Teflon
0.50
Kapton
0.40
LampWick
Pyrell
0.30
Silicone
0.20
0.10
0.00
0
500
1000
1500
2000
Figure 8: Diameter of average mass versus the aging time for 5 materials at 8 cm/s airflow at the baseline temperature
for each sample.
A series of tests were conducted in normal gravity to duplicate the baseline flight conditions (8 cm/s air speed and the
fuel temperatures needed to release 1 to 2 mg of smoke in 60 seconds). The aging duration was 720 seconds. The
diameter of average mass from the low-gravity is plotted versus the results from the normal gravity testing and shown in
figure 9. Overall the results correlate strongly with a slope of 1. This suggests that at air flow rates of 8 cm/s or higher,
the size of smoke particulate in microgravity is well predicted by normal gravity testing. Since much of the habitable
volumes of current spacecraft have ventilation flows in that range, normal gravity testing may indeed be an adequate
predictor of microgravity smoke. The potential error can be estimated using figure 7 which suggests that lower flow
rates could increase the diameter of average mass by as much as a factor of 2.5. Nevertheless, these results suggest that
normal-gravity testing may be an adequate engineering solution.
9
Diameter of Average Mass: low-gravity versus normal gravity
Diameter of Average Mass, low-gravity results (µm)
0.8
Teflon, Baseline Temperature
0.7
Teflon,High Temperature
Teflon, Baseline Temperature, Aged
0.6
Kapton, Baseline Temperature
Kapton, High Temperature
0.5
Kapton, Baseline Temperature, Aged
Kapton, High Temperature, Aged
0.4
Lampwick, Baseline Temperature
Lampwick, Hig [E-16c3dee3b5bc4d1c]
- The Spacecraft Fire Experiment (Saffire) - Objectives, Development and Status — recorded page 1 (physical PDF page unverified): hicle.
This duct will provide a uniform flow across the
samples, maintain a clear flow path within the
experiment module, and prevent burning debris from
interacting with the rest of the cargo. The sample card is
positioned in the center of the flow duct as shown in
Fig. 1.
2.1 Sample Materials
The sample material for Saffire-I and III is a composite
fabric consisting of cotton on a fiberglass substrate
(75% cotton, 25% fiberglass by weight). It is called
SIBAL cloth because it was developed for the Solid
Inflammability Boundary at Low-Speeds (SIBAL)
spaceflight experiment and has been used in many space
experiments because it burns like cotton but maintains
structural integrity after the cotton is consumed. The
objective of the Saffire-I and III tests will be to
determine how rapidly a large-scale fire grows in lowgravity and whether it reaches a steady-state spread rate.
Saffire-I will be conducted at an air flow velocity of 20
Figure 1: Schematic of the Spacecraft Fire Safety
Demonstration Experiment. The experiment module
consists of a flow duct containing the sample card
and an avionics bay. All power, computer, and data
acquisition modules are contained in the bay. The
experiment module is approximately 53- by 90- by
133-cm.
cm/s while Saffire-III will be run at a flow velocity of
30 cm/s .
Saffire-II has a sample card that contains 9 samples,
each 5 cm x 29 cm. Table 1 lists the samples contained
on Saffire-II while Fig. 2 shows their locations on the
sample card. These materials were selected because they
have normal gravity Maximum Oxygen Concentration
(MOC) flammability limits that indicate they will burn
in normal gravity just above and below 21% O2 by
volume, i.e., the expected concentration of O2 when
1
2
3
4
5
6
7
8
9
SIBAL
Silicone
Silicone
opposed
PMMA
Nomex
Air Flow
Figure 2: Sample layout for Saffire-II
Sample
Number
Material
Sample
Thickness
Air Flow
(cm/s)
Igniter
Position
S1
Silicone
0.25 mm
20
Upstream
and atmospheric parameters. The diagnostic suite used
in Saffire are shown in Table 2. The primary experiment
data will be provided by two cameras that view one side
of the sample card.
S2
Silicone
0.61 mm
20
Upstream
2.3 Experiment Development
S3
Silicone
1.02 mm
20
Upstream
S4
Silicone
0.36 mm
20
Downstream
S5
SIBAL fabric
0.33 mm
20
Upstream
S6
SIBAL fabric
0.33 mm
30
Upstream
S7
PMMA to
Nomex
0.33 mm
20
Upstream
20
Upstream
30
Upstream
The Saffire flight systems (hardware and software)
underwent the NASA flight experiment development
reviews and testing although these processes were
heavily tailored to realize savings in cost and schedule.
Because all three units were being developed in parallel,
some components were ready to progress to the next
development phase before the entire system for all three
units had completed that phase. The logic behind the
tailoring was to tailor the review criteria to allow
components that were ready to progress onto the next
development phase while the remainder of the system
was completed. Given the design of the system and the
risk tolerance advocated by the Advanced Exploration
Systems Division, this approach was warranted. A
Mission Concept Review/System Requirements Review
was held in November 2012 and followed
approximately 7 months later by a Periodic Technical
Review-1 (PTR-1) that combined NASA’s typical
Preliminary Design Review/Critical Design Review.
Table 1. Saffire-II Samples
S8
Structured
PMMA
S9
Flat PMMA
10 mm (with
tapered edge
for ignition)
10 mm (with
tapered edge
for ignition)
Cygnus unberths from ISS. Drop tower testing has
demonstrated the MOC flammability limits of a material
can be different in low-g than in normal gravity [3-5].
Therefore, the objective of the Saffire-II tests is to
quantify that affect in long-duration low-gravity using
samples of the same size as those used in the in NASASTD-6001 Test 1 normal-gravity tests [3]. Some of
these samples are expected to burn while others may
not.
Quantifying the difference in flammability limits  [E-9df910ff0e083254]

## Coverage and limitations

Related evidence is not equivalent evidence. Missing direct evidence is not a NASA research gap.

## Sources

- Combustion of Solids in Microgravity: Results from the BASS-II Experiment — ntrs-20160000593, Approach; https://ntrs.nasa.gov/citations/20160000593 [E-context-5227141f2aaa7feb2e37]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II terrestrial reference tests; https://ntrs.nasa.gov/citations/20170008805 [E-context-a79df97c23d629116824]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II silicone results; https://ntrs.nasa.gov/citations/20170008805 [E-context-d86d030e275ce04b8b82]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Saffire-II silicone ground and flight tests; https://ntrs.nasa.gov/citations/20170008805 [E-context-ec300b3756c4bd69021b]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, Summary and Conclusions; https://ntrs.nasa.gov/citations/20170008805 [E-context-4679bc2d5e96d1425335]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170008805 [E-49fde889c36ce643]
- Joint Launch + One Year Science Review of USML-1 and USMP-1 with the Microgravity Measurement Group — ntrs-20030075796, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20030075796 [E-d272290480488dc5]
- Results of Large-Scale Spacecraft Flammability Tests — ntrs-20170008805, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170008805 [E-7ab386873c223183]
- Microgravity smoldering combustion on the USML-1 Space Shuttle mission — ntrs-19960008388, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/19960008388 [E-1f2be6f603bde68c]
- Evaluation of Low-Gravity Smoke Particulate for Spacecraft Fire Detection — ntrs-20140006579, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20140006579 [E-16c3dee3b5bc4d1c]
- The Spacecraft Fire Experiment (Saffire) - Objectives, Development and Status — ntrs-20170001636, recorded page 1 (physical PDF page unverified); https://ntrs.nasa.gov/citations/20170001636 [E-9df910ff0e083254]
