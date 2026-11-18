> Public-copy note: manufacturer PDFs are not redistributed. Links open official sources; mentions of retained archives describe the privately inspected source evidence. Source and delivered hashes differ where paths or links were adapted; see repository-copy-receipt.json.

# Control options and switchboard choices

**Master SHA-256:** `b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac`. Review/quotation only; no construction or product approval. The homeowner's current choice is **fixed-white lighting, local brightness control, no extra curtain knob and one larger living LOW supply**.

| Control route | Current plan | What the buyer / electrician must prove |
|---|---|---|
| Single-colour 24 V CV PWM wall knob | **Selected concept** for the 21 LOW, task and other 24 V knob groups. Four warm curtain strips follow their room's existing LOW knob. | Exact strip + CV supply + controller + repeater compatibility; complete branch ratings, fault protection, wiring, box fit, flicker, low-end start and memory. |
| 230 V LED phase-cut dimming | **Selected concept**, ten mains-dimmer groups including the separate 48 V track driver/control chain. | Fitting maker must list the exact driver/dimmer and permitted edge. Confirm actual input VA, driver count, inrush, ambient, flicker and noise. Every group is on procurement hold. |
| Integral reader / PIR controls | Six fitting-mounted controls, plus eight conceptual on/off switch modules in selected locations. | Fit, access, local ON/AUTO/OFF override where specified, low-level behaviour, power loss and any wet-area requirements. They are not six additional wall dimmers. |
| Simple switching or split-group alternative | Only a **fallback** if an acceptable dimming chain cannot be sourced; it does not meet the homeowner's current request for dimming every specified group. | If considered, show the lost dimming/changed wall controls to the homeowner before any redesign. Do not merge LOW and HIGH to make a load large enough for a dimmer. |
| Other wired controls or automation | Not part of the selected package. A documented alternative may be evaluated later without sacrificing independent local operation. | Any protocol, interface, supply, commissioning and service changes need a separately engineered and approved proposal; no internet or app may become mandatory. |

## Living LOW and controller limits

The homeowner chose one **P01 24 V, 480 W planning-class supply** for C03, C04, C05 and X-CURT-LIV. P03 is removed. One K-LIV-LOW knob, **six modeled outputs and two modeled repeaters** serve 181.52 W of strip load. Added controller and cable losses are not included. Supply, repeater and protection topology remain **HOLD**; the previous living voltage-drop and LT-4/LT-5 inrush passes are invalid.

The Skydance T1-K is a source-backed **candidate**, not a purchased or approved model: 12-48 V input, three output channels rated 4 A each, 12.5 A maximum input and 2 or 8 kHz selection according to its manual. The project used an **assumed** 2.4 A/output screening limit at 2 kHz; the manufacturer warns that the higher frequency reduces output capacity. The 480 W reference PSU has a 20 A nameplate output, so the complete fault-protected distribution and controller input must be engineered. A generic PWM repeater is not automatically suitable.

The 0.60 sizing factor is **0.80 assumed thermal x 0.75 assumed utilization**, not a manufacturer rule. The 181.52 W strip load needs 303 W minimum when rounded up under that assumption; 480 W provides a 288 W planning allowance. Actual input, temperature, case measurement, protective coordination and losses remain for professional validation.

## Mains dimmer sourcing

The India-listed Legrand Lyncus **677304** is a manufacturer-page lead describing **3-50 W and up to eight LED lamps**; wording elsewhere on its page is inconsistent. It is not approved with any planned luminaire. For example, living C01 is **40 W / five modeled fixtures**, a nominal comparison only; bedroom C20 is **48 W / eight fixtures**, at/near the listed limits before real driver input and derating. The 48 V track group is not evaluated by a downlight rating.

Legrand Arteor Advance **AA24107MB** and Schneider AvatarOn **E8331RD250_WE** have LED **VA**, not simply W, ranges in their manufacturer sheets. Obtain actual power factor and AC input; `VA = input W / power factor` is only a preliminary check. Their phase mode, lamp count, wall-box temperature/size and exact driver approval must be confirmed. See `source-index.md` and `schedules/mains-dimmer-check.csv`. A fan regulator is not an LED dimmer.

## Switchboards and room intent

`schedules/switchboard-schedule.csv` groups controls and conceptual switch points by board. `wall-control-schedule.csv` lists the 31 wall controls; `fitting-controls.csv` lists the four readers and two PIR lights. Board coordinates are planning references, not surveyed positions or final plate layouts.

Keep the pooja base strip **C06A** and the shadow-sensitive spot **C06B** independently dimmable. Keep C10 passage dimmable. Bathroom face lights have an independent control. CBR H1-H6 are released for review, but C37 dimmer procurement remains held. Four flats have separate neutrals, supplies and control domains; common stairs use a distinct building circuit.

Only the supplier and qualified electrician can approve actual electrical protection, earthing, isolation, cable sizes, wet-zone suitability, driver locations, switchboard fit and current standards. User choices establish preferred experience, not a permit to buy or wire equipment.
