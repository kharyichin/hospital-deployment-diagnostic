import json
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Hospital Deployment Planning Diagnostic",layout="wide")
st.markdown("<style>.block-container{max-width:1280px;padding-top:2rem}h1,h2,h3{letter-spacing:-.025em}[data-testid='stMetric']{background:#f4f8f7;border:1px solid #d6e3df;padding:14px;border-radius:8px}</style>",unsafe_allow_html=True)

EXAMPLES={
 "Current assessment":("Not selected","Not confirmed","Not confirmed","Not confirmed"),
 "Example 1: Existing systems and connections are ready":("Multi-hospital regional system","Central staffing team","Documented and confirmed","Named"),
 "Example 2: Systems exist, but rules and connections need preparation":("Academic medical center","Department-level managers","Written, but some rules need confirmation","Named"),
 "Example 3: A required HR system is being replaced":("Multi-hospital regional system","Central staffing team","Written, but some rules need confirmation","Named")}
ROWS={
 list(EXAMPLES)[1]:[["Employee IDs and department assignments","Workday","Available and stable","Direct connection","Yes","Not needed","Document reviewed"],["Qualifications and shift eligibility","QGenda","Available and stable","Direct connection","Yes","Not needed","Observed in practice"],["Patient demand and required coverage","Epic","Available and stable","Direct connection","Yes","Not needed","Document reviewed"]],
 list(EXAMPLES)[2]:[["Employee IDs and department assignments","Workday","Available and stable","Existing file transfer","Yes","Not needed","Document reviewed"],["Qualifications and shift eligibility","QGenda","Available and stable","Not confirmed","Yes","Not confirmed","Not confirmed"],["Patient demand and required coverage","Epic","Available and stable","New connection required","Yes","Not confirmed","Reported by stakeholder"]],
 list(EXAMPLES)[3]:[["Employee IDs and department assignments","Workday","Being replaced","Not confirmed","Yes","Allowed for first department","Reported by stakeholder"],["Qualifications and shift eligibility","QGenda","Available and stable","Direct connection","Yes","Not needed","Observed in practice"],["Patient demand and required coverage","Epic","Available and stable","Direct connection","Yes","Not needed","Document reviewed"]]}
SOLUTIONS={"Workforce management":["Creating and balancing schedules","Managing vacant shifts and staff outreach","Shift pickup and swaps","Time-off management","Staff deployment across departments","Pay coding","Staffing recommendations based on patient demand"],"Flow and capacity operations":["Patient-surge forecasting","Discharge forecasting","Identifying patient-flow bottlenecks","Connecting capacity forecasts to staffing decisions"],"Executive analytics":["Staffing-risk alerts","Visibility across hospitals and departments","Labor and capacity reporting"]}
INFO=["Employee IDs and department assignments","Qualifications and shift eligibility","Availability and approved leave","Existing rosters and vacant shifts","Patient demand and required coverage","Actual worked hours","Payroll codes"]
SYSTEMS=["Workday","Oracle PeopleSoft","Oracle Fusion Cloud HCM","UKG Pro WFM / Dimensions","UKG Workforce Central / Kronos","QGenda","symplr Smart Square","M7","Epic","MEDITECH","Spreadsheet or paper","Other","Not confirmed"]

def status(r):
    if r["Required before first launch"]=="No":return "Not required for first launch"
    if r["How this was checked"]=="Not confirmed":return "Needs confirmation"
    if r["Source status"]=="Available and stable" and r["Transfer method"] not in ["New connection required","Not confirmed"]:return "Ready"
    if r["Source status"] in ["Being replaced","New system being introduced","Not available"]:return "Temporary route available" if r["Temporary route"]=="Allowed for first department" else "Must wait"
    if r["Transfer method"]=="New connection required":return "Connection required"
    return "Needs confirmation"

def recommend(df,rules,owner):
    s=df.Status.tolist()
    if "Must wait" in s:return "Wait for the required source system","Required information is unavailable and the hospital has not approved another way to provide it."
    if "Temporary route available" in s:return "Prepare the first department while deciding whether to use a temporary information transfer","A required system is changing. Discovery and preparation can continue, but complete testing needs either the temporary transfer or the replacement system."
    if "Needs confirmation" in s:return "Complete the unresolved assessment before committing to the launch plan","At least one required information source, transfer method or owner has not been confirmed."
    if "Connection required" in s:return "Prepare the first department while the required connection is built","Rules and connection work can proceed together. Complete testing waits for both."
    if rules!="Documented and confirmed":return "Use the existing systems while local rules are confirmed","The required information is available, but the workflow cannot be set up correctly until its operating rules are confirmed."
    if owner!="Named":return "Name the hospital decision owner before configuration","The required information is available, but no one has been named to approve decisions and exceptions."
    return "Use the existing systems for a controlled first-department launch","The reported operating rules, decision owner and required information are ready for setup and testing."

TOUR_STEPS=[
    ("Choose a starting point","Open an example to see how conditions change the plan, or choose Current assessment for a real case.","choose-an-assessment"),
    ("Complete the assessment","Record the scope, current process, operating rules and information needed for the first rollout.","1-hospital-and-rollout-assessment"),
    ("Review the rollout plan","See what can start now, what needs resolution and who needs to act.","2-recommended-rollout-plan"),
    ("Save the work","Download the action plan, timeline or full assessment for the team.","6-download-working-files"),
]

if "tour_step" not in st.session_state:st.session_state.tour_step=0
if "tour_open" not in st.session_state:st.session_state.tour_open=True
if "tour_finished" not in st.session_state:st.session_state.tour_finished=False

@st.dialog("Quick tour")
def show_tour():
    step=st.session_state.tour_step
    title,body,anchor=TOUR_STEPS[step]
    st.caption(f"Step {step+1} of {len(TOUR_STEPS)}")
    st.progress((step+1)/len(TOUR_STEPS))
    st.subheader(title)
    st.write(body)
    left,middle,right=st.columns([1,1,1.4])
    if step>0 and left.button("Back",use_container_width=True):
        st.session_state.tour_step-=1
        st.session_state.tour_scroll_target=TOUR_STEPS[st.session_state.tour_step][2]
        st.rerun()
    if middle.button("End tour",use_container_width=True):
        st.session_state.tour_open=False;st.session_state.tour_finished=True;st.rerun()
    label="Next" if step<len(TOUR_STEPS)-1 else "Finish tour"
    if right.button(label,type="primary",use_container_width=True):
        if step<len(TOUR_STEPS)-1:
            st.session_state.tour_step+=1
            st.session_state.tour_scroll_target=TOUR_STEPS[st.session_state.tour_step][2]
        else:
            st.session_state.tour_scroll_target=anchor
            st.session_state.tour_open=False
            st.session_state.tour_finished=True
        st.rerun()

title_col,tour_col=st.columns([5,1])
title_col.title("Hospital Deployment Planning Diagnostic")
tour_col.write("")
if tour_col.button("Quick tour",use_container_width=True):
    if st.session_state.tour_finished:st.session_state.tour_step=0;st.session_state.tour_finished=False
    st.session_state.tour_open=True;st.rerun()
st.write("Assess the proposed rollout, identify what controls the first launch, and build a practical hospital-specific plan.")

target=st.session_state.pop("tour_scroll_target",None)
if target is not None:
    components.html(f"<script>setTimeout(()=>window.parent.document.getElementById('{target}')?.scrollIntoView({{behavior:'smooth',block:'start'}}),500);</script>",height=0)
if st.session_state.tour_open:show_tour()

st.markdown('<span id="choose-an-assessment"></span>',unsafe_allow_html=True)
uploaded=st.file_uploader("Resume a saved assessment",type="json",help="Upload a full assessment previously downloaded from this page.")
loaded={};form_key="new"
if uploaded is not None:
    try:
        loaded=json.load(uploaded);form_key=f"{uploaded.name}:{uploaded.size}"
        st.success("Saved assessment loaded. Review the answers before continuing.")
    except (json.JSONDecodeError,UnicodeDecodeError,AttributeError):
        st.error("This file could not be read. Upload a JSON file downloaded from this assessment.")
loaded_choice=loaded.get("selection") if loaded.get("selection") in EXAMPLES else None
choice=st.selectbox("Choose an assessment",list(EXAMPLES),index=list(EXAMPLES).index(loaded_choice) if loaded_choice else 1,key=f"choice:{form_key}",help="Choose Current assessment for a new hospital. The examples demonstrate how different conditions change the recommendation.")
st.caption("Examples use a fictional ICU rollout. Change any answer to see how the plan changes.")
if st.button("Reset this selection"):
    for key in list(st.session_state):
        if choice in str(key): del st.session_state[key]
    st.rerun()
profile0,governance0,rules0,owner0=EXAMPLES[choice]
loaded_scope=loaded.get("scope",{})
loaded_context=loaded.get("hospital_context",{})

st.header("1. Hospital and rollout assessment")
st.info("Answers reflect the information available today. Record how each system answer was checked, then verify the workflow with the responsible hospital teams during discovery.")
a,b,c,d=st.tabs(["1. Scope of work","2. Current process","3. Rules and ownership","4. Systems and information"])
with a:
    x,y=st.columns(2)
    solution_options=list(SOLUTIONS);solution_default=loaded_scope.get("solution") if loaded_scope.get("solution") in solution_options else solution_options[0]
    solution=x.selectbox("Deployment scope",solution_options,index=solution_options.index(solution_default),key=f"solution:{form_key}",help="Choose the hospital workflow this assessment will plan. Keep the first rollout narrow enough to test completely.")
    loaded_capabilities=[item for item in loaded_scope.get("capabilities",[]) if item in SOLUTIONS[solution]]
    capabilities=x.multiselect("Capabilities included in the first rollout",SOLUTIONS[solution],default=loaded_capabilities or SOLUTIONS[solution][:2],key=f"capabilities:{form_key}",help="Select only the capabilities intended for the first ward, department or hospital.")
    department=y.text_input("First ward or department",value=loaded_scope.get("department","ICU"),key=f"department:{form_key}")
    staff_options=["Nurses","Nurse managers","Central staffing team","Allied health","Physicians or advanced practice providers","Hospital executives","Other"]
    staff=y.multiselect("Staff groups included",staff_options,default=[item for item in loaded_scope.get("staff_groups",["Nurses","Nurse managers","Central staffing team"]) if item in staff_options],key=f"staff:{form_key}")
    sites=y.number_input("Hospitals included in the first rollout",1,value=int(loaded_scope.get("hospitals",1)),key=f"sites:{form_key}")
with b:
    x,y=st.columns(2)
    profiles=["Not selected","Academic medical center","Multi-hospital regional system","Community or rural hospital"]
    profile_default=loaded_context.get("type",profile0);profile=x.selectbox("Hospital type",profiles,index=profiles.index(profile_default) if profile_default in profiles else 0,key=f"profile:{form_key}")
    governance_options=["Central staffing team","Department-level managers","Shared between central and department teams","Not confirmed"];governance_default=loaded_context.get("current_owner",governance0)
    governance=x.selectbox("Who currently manages this work?",governance_options,index=governance_options.index(governance_default) if governance_default in governance_options else 3,key=f"governance:{form_key}")
    manual_options=["Workforce software","Spreadsheets","Calls or texts","Paper forms","Manual entry between systems","None identified","Not confirmed"]
    manual=y.multiselect("How is this work completed today?",manual_options,default=[item for item in loaded_context.get("manual_work",["None identified"] if choice==list(EXAMPLES)[1] else ["Spreadsheets"]) if item in manual_options],key=f"manual:{form_key}")
    variation_options=["Same process in first-wave departments","Some local differences","Process differs by department","Not confirmed"];variation_default=loaded_context.get("process_variation",variation_options[0])
    variation=y.selectbox("Does the process differ between departments?",variation_options,index=variation_options.index(variation_default) if variation_default in variation_options else 3,key=f"variation:{form_key}")
    exception_options=["Sick calls","Vacant shifts","Shift swaps","Overtime approval","Float staff","Staff reassignment","Downtime or connection failure","Not confirmed"]
    exceptions=y.multiselect("Which situations regularly require manual decisions?",exception_options,default=[item for item in loaded_context.get("exceptions",["Vacant shifts"]) if item in exception_options],key=f"exceptions:{form_key}")
with c:
    x,y=st.columns(2); rule_options=["Documented and confirmed","Written, but some rules need confirmation","Used in practice but not fully documented","Not documented","Not confirmed"]
    rules_default=loaded_context.get("rules",rules0);rules=x.selectbox("How are the current operating rules recorded?",rule_options,index=rule_options.index(rules_default) if rules_default in rule_options else 4,key=f"rules:{form_key}")
    labor_options=["Union or contract rules apply","No union or contract rules identified","Not confirmed"];labor_default=loaded_context.get("labor_rules",labor_options[0])
    labor=x.selectbox("Do union or employment-contract rules apply?",labor_options,index=labor_options.index(labor_default) if labor_default in labor_options else 2,key=f"labor:{form_key}")
    owner_options=["Named","Not named","Not confirmed"];owner_default=loaded_context.get("decision_owner",owner0)
    owner=y.selectbox("Is a hospital decision-maker named for this scope?",owner_options,index=owner_options.index(owner_default) if owner_default in owner_options else 2,key=f"owner:{form_key}")
    approver_options=["Nursing operations","Department managers","Central staffing office","Hospital IT","HR or payroll","Labor Relations","Information security or privacy","Not confirmed"]
    approvers=y.multiselect("Who must approve changes to this workflow?",approver_options,default=[item for item in loaded_context.get("approvers",["Nursing operations","Hospital IT"]) if item in approver_options],key=f"approvers:{form_key}")
with d:
    columns=["Information needed","Source system","Source status","Transfer method","Required before first launch","Temporary route","How this was checked"]
    default=loaded.get("information_dependencies") or ROWS.get(choice,[["Employee IDs and department assignments","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Qualifications and shift eligibility","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Patient demand and required coverage","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"]])
    raw=pd.DataFrame(default);raw=raw[columns] if set(columns).issubset(raw.columns) else pd.DataFrame(default,columns=columns)
    flows=st.data_editor(raw,hide_index=True,width="stretch",num_rows="dynamic",key=f"flows:{choice}:{form_key}",column_config={"Information needed":st.column_config.SelectboxColumn(options=INFO),"Source system":st.column_config.SelectboxColumn(options=SYSTEMS),"Source status":st.column_config.SelectboxColumn(options=["Available and stable","Being replaced","New system being introduced","Not available","Not confirmed"]),"Transfer method":st.column_config.SelectboxColumn(options=["Direct connection","Existing scheduled file","File upload","Manual entry","Same system","New connection required","Not confirmed"]),"Required before first launch":st.column_config.SelectboxColumn(options=["Yes","No"]),"Temporary route":st.column_config.SelectboxColumn(options=["Not needed","Allowed for first department","Not allowed","Not confirmed"]),"How this was checked":st.column_config.SelectboxColumn(options=["Reported by stakeholder","Document reviewed","Observed in practice","Tested successfully","Not confirmed"])})

df=flows.copy();df["Status"]=df.apply(status,axis=1); required=df[df["Required before first launch"]=="Yes"]
route,reason=recommend(df,rules,owner); critical=required[required.Status.isin(["Must wait","Temporary route available","Connection required","Needs confirmation"])]
critical_text="None" if critical.empty else f'{critical.iloc[0]["Information needed"]} from {critical.iloc[0]["Source system"]}'
items_to_resolve=len(critical)+int(rules!="Documented and confirmed")+int(owner!="Named")

st.header("2. Recommended rollout plan")
st.subheader("What this assessment found")
st.markdown(f"**Recommended approach**  \n{route}")
st.markdown(f"**Why**  \n{reason}")
ready_required=required[required.Status=="Ready"]
ready_details=[f'{r["Information needed"]} — {r["Source system"]}, {r["Transfer method"].lower()}' for _,r in ready_required.iterrows()]
action_details=[]
if owner!="Named":action_details.append("Hospital decision-maker")
if rules!="Documented and confirmed":action_details.append("Operating rules and exceptions")
action_details.extend([f'{r["Information needed"]} — {r["Source system"]}' for _,r in critical.iterrows()])
m1,m2,m3=st.columns(3)
m1.metric("First rollout",department);m1.caption(f"{len(capabilities)} capabilities included")
m2.metric("Required information reported ready",f'{len(ready_required)} of {len(required)}')
if ready_details:m2.caption("Ready:  \n"+"  \n".join(f"• {item}" for item in ready_details))
else:m2.caption("No required information has been confirmed as ready.")
m3.metric("Items to resolve before complete testing",items_to_resolve)
if action_details:m3.caption("Resolve:  \n"+"  \n".join(f"• {item}" for item in action_details))
else:m3.caption("Nothing identified from the current answers.")

if critical.empty and rules=="Documented and confirmed" and owner=="Named":
    can_start=f"Set up the {department} workflow, give test users access and prepare normal and exception scenarios."
else:
    can_start=f"Observe the current {department} workflow, confirm the first rollout scope and begin work that does not depend on unresolved information."
resolve=[]
if owner!="Named":resolve.append("Name the hospital decision-maker for this rollout.")
if rules!="Documented and confirmed":resolve.append("Confirm the operating rules and exceptions used by the first department.")
for _,r in critical.iterrows():
    issue_text={"Needs confirmation":"the source or transfer method has not been confirmed","Connection required":"a new connection must be built and tested","Temporary route available":"the source system is changing, but a temporary transfer may be used","Must wait":"the information is unavailable and no alternative has been approved"}[r["Status"]]
    resolve.append(f'{r["Information needed"]} from {r["Source system"]}: {issue_text}.')
left,right=st.columns(2)
with left:
    st.markdown("**What can start now**")
    st.write(can_start)
with right:
    st.markdown("**Resolve before complete testing**")
    if resolve:
        for item in resolve:st.write(f"• {item}")
    else:st.write("Nothing identified. The reported rules, ownership and required information are ready for testing.")

plan=[[False,1,"Observe the current workflow, exceptions and baseline for the selected scope.","Every rollout needs an observed starting point before configuration.","Deployment team","Hospital operations and intended users","Days 1–3"]]
if owner!="Named":plan.append([False,len(plan)+1,"Name the hospital decision-maker for the first rollout.","The assessment does not have a confirmed decision owner.","Hospital sponsor","Deployment team and department leadership","Days 1–3"])
if rules!="Documented and confirmed":plan.append([False,len(plan)+1,"Confirm the first department's operating rules and exceptions.",f'Current rules are recorded as: {rules.lower()}.' ,"Deployment team","Department managers and Nursing operations"+("; Labor Relations" if labor=="Union or contract rules apply" else ""),"Days 4–7"])
for _,r in critical.iterrows():
    if r["Status"]=="Needs confirmation":action=f'Confirm the source and transfer method for {r["Information needed"].lower()} from {r["Source system"]}.'
    elif r["Status"]=="Connection required":action=f'Build and test the transfer of {r["Information needed"].lower()} from {r["Source system"]}.'
    elif r["Status"]=="Temporary route available":action=f'Agree and test a temporary way to transfer {r["Information needed"].lower()} from {r["Source system"]}.'
    else:action=f'Confirm when {r["Information needed"].lower()} from {r["Source system"]} will be available, or approve another source.'
    plan.append([False,len(plan)+1,action,f'The assessment marked this information as: {r["Status"].lower()}.',"Source-system owner","Hospital IT and the deployment team","Days 4–10; complete before testing"])
plan.append([False,len(plan)+1,"Test normal work, exceptions and recovery through the complete workflow.","Testing confirms that the configured workflow works with the agreed rules and required information.","Deployment team","Intended users and Hospital IT",f'Do after items 1–{len(plan)}'])
st.subheader("Execution tracker")
st.write("These actions are generated from the assessment above. Update the timing and mark each item complete as the work progresses.")
plan_df=pd.DataFrame(plan,columns=["Done","Item","Action","Why this action appears","Owner","Supporting parties","Timing / status"])
saved_plan=loaded.get("action_plan")
if saved_plan:
    saved_plan_df=pd.DataFrame(saved_plan)
    if set(plan_df.columns).issubset(saved_plan_df.columns):plan_df=saved_plan_df[plan_df.columns]
plan_df=st.data_editor(plan_df,hide_index=True,width="stretch",disabled=["Item","Action","Why this action appears","Owner","Supporting parties"],key=f"plan:{choice}:{form_key}",column_config={"Done":st.column_config.CheckboxColumn(width="small"),"Item":st.column_config.NumberColumn(width="small"),"Action":st.column_config.TextColumn(width="large"),"Why this action appears":st.column_config.TextColumn(width="large"),"Timing / status":st.column_config.TextColumn(help="Examples: Days 1–3; Do after item 2; Ongoing; Completed")})
completed=int(plan_df["Done"].sum())
open_actions=len(plan_df)-completed
st.markdown(f'<span style="display:inline-block;background:#dcefe5;color:#155b39;padding:4px 10px;border-radius:999px;font-weight:600">{completed} completed</span> <span style="display:inline-block;background:#e7eef5;color:#174e68;padding:4px 10px;border-radius:999px;font-weight:600">{open_actions} remaining</span>',unsafe_allow_html=True)
st.progress(completed/len(plan_df));st.caption(f"{completed} of {len(plan_df)} actions completed")
def color_status(value):
    colors={"Ready":"background-color:#dcefe5;color:#155b39;font-weight:600","Temporary route available":"background-color:#fff0c9;color:#765100;font-weight:600","Connection required":"background-color:#dcecf4;color:#174e68;font-weight:600","Needs confirmation":"background-color:#eceeef;color:#39434a","Must wait":"background-color:#f6dddd;color:#7b2424;font-weight:600"}
    return colors.get(value,"")
st.subheader("Information and data gaps")
dependency_view=df[df.Status!="Ready"][["Information needed","Source system","Source status","Transfer method","How this was checked","Status"]]
if dependency_view.empty:st.success("No information or data gaps are identified from the current answers.")
dependency_style=(dependency_view.style
    .map(color_status,subset=["Status"])
    .set_properties(**{"white-space":"normal","overflow-wrap":"anywhere"})
    .set_properties(subset=["Information needed"],**{"min-width":"230px"})
    .set_properties(subset=["How this was checked"],**{"min-width":"190px"})
    .set_properties(subset=["Status"],**{"min-width":"190px","white-space":"normal"}))
if not dependency_view.empty:st.dataframe(dependency_style,hide_index=True,width="stretch",height=min(420,80+len(dependency_view)*52))
with st.expander("View all required information paths"):
    st.dataframe(df[["Information needed","Source system","Source status","Transfer method","How this was checked","Status"]],hide_index=True,width="stretch")

st.header("3. Estimated timeline")
st.write("Recommended planning time. Edit the ranges when hospital or vendor estimates are available.")
complexity=int(sites>1)+int(variation!="Same process in first-wave departments")+int(labor=="Union or contract rules apply")+int(profile=="Academic medical center"); connections=int(required.Status.isin(["Connection required","Temporary route available","Must wait","Needs confirmation"]).sum())
timing=pd.DataFrame([["Workflow discovery",1,2+min(complexity,2),"Access to department operators"],["Rule confirmation",1,1+(2 if rules!="Documented and confirmed" else 0)+(1 if labor=="Union or contract rules apply" else 0),"Observed workflow"],["Information and connection preparation",1,2+connections*2,"Confirmed sources, access and owners"],["Configuration and complete workflow testing",2,3,"Confirmed rules and usable information paths"],["User preparation and controlled launch",1,2,"Completed workflow testing"]],columns=["Work package","Recommended minimum weeks","Recommended maximum weeks","Must be completed first"])
saved_timing=loaded.get("timeline")
if saved_timing:
    saved_timing_df=pd.DataFrame(saved_timing)
    if set(timing.columns).issubset(saved_timing_df.columns):timing=saved_timing_df[timing.columns]
timing=st.data_editor(timing,hide_index=True,width="stretch",disabled=["Work package","Must be completed first"],key=f"time:{choice}:{form_key}")
vals=[(float(r.iloc[1]),float(r.iloc[2])) for _,r in timing.iterrows()]; starts=[(0,0),vals[0],vals[0],(vals[0][0]+max(vals[1][0],vals[2][0]),vals[0][1]+max(vals[1][1],vals[2][1])),(0,0)];starts[4]=(starts[3][0]+vals[3][0],starts[3][1]+vals[3][1]);total=(starts[4][0]+vals[4][0],starts[4][1]+vals[4][1])
st.metric("Estimated time to first-department launch",f"{total[0]:g}–{total[1]:g} weeks")
fig=go.Figure(); colors=["#177e89","#4d8f7f","#d08a33","#635b8f","#2b6e7d"]
for i,r in timing.iterrows():fig.add_trace(go.Bar(name=r["Work package"],y=["Recommended plan"],x=[r["Recommended maximum weeks"]],base=[starts[i][1]],orientation="h",marker_color=colors[i],text=f'Week {int(starts[i][1])+1}–{int(starts[i][1]+r["Recommended maximum weeks"])}',textposition="inside"))
fig.update_layout(barmode="overlay",xaxis_title="Week",xaxis=dict(dtick=1),height=240,margin=dict(l=0,r=0,t=10,b=0));st.plotly_chart(fig,width="stretch")
st.caption("Rule confirmation and information preparation occupy the same weeks. Testing starts after both are complete. All ranges are editable planning assumptions.")

st.subheader("Planning estimates")
effort=pd.DataFrame([
    ["Workflow discovery",3,5+complexity],
    ["Rule confirmation",2,3+complexity],
    ["Information and connection preparation",3,5+connections*2],
    ["Configuration and workflow testing",5,8+connections],
    ["User preparation and controlled launch",3,5+min(complexity,2)],
],columns=["Work package","Estimated minimum person-days","Estimated maximum person-days"])
saved_effort=loaded.get("effort_estimate")
if saved_effort:
    saved_effort_df=pd.DataFrame(saved_effort)
    if set(effort.columns).issubset(saved_effort_df.columns):effort=saved_effort_df[effort.columns]
effort=st.data_editor(effort,hide_index=True,width="stretch",disabled=["Work package"],key=f"effort:{choice}:{form_key}")
effort_min=float(effort["Estimated minimum person-days"].sum());effort_max=float(effort["Estimated maximum person-days"].sum())
average_fte_min=effort_min/max(total[1]*5,1);average_fte_max=effort_max/max(total[0]*5,1)
e1,e2=st.columns(2)
e1.metric("Estimated deployment-team effort",f"{effort_min:g}–{effort_max:g} person-days")
e2.metric("Estimated average deployment-team capacity",f"{average_fte_min:.1f}–{average_fte_max:.1f} FTE")
st.markdown("*Planning estimate only. Person-days and average FTE are derived from the selected conditions and editable assumptions, not observed staffing data.*")

with st.expander("Estimate a later rollout wave"):
    ex1,ex2,ex3=st.columns(3)
    next_departments=ex1.number_input("Departments in the next wave",1,value=max(2,len(capabilities)),key=f"next_departments:{form_key}")
    next_hospitals=ex2.number_input("Hospitals in the next wave",1,value=max(1,int(sites)),key=f"next_hospitals:{form_key}")
    reuse=ex3.selectbox("How much of the first rollout can be reused?",["Most of it","Some of it","Very little"],key=f"reuse:{form_key}")
    reuse_ranges={"Most of it":(2,4),"Some of it":(4,7),"Very little":(6,10)}
    wave_min,wave_max=reuse_ranges[reuse]
    wave_min+=max(0,next_hospitals-1);wave_max+=max(0,next_hospitals-1)*2+max(0,next_departments-2)
    st.metric("Estimated time for the next rollout wave",f"{wave_min}–{wave_max} weeks")
    st.markdown("*Scenario estimate for planning. It assumes departments within the wave can overlap and must be replaced with actual results from the first rollout.*")

st.header("4. Potential issues and flags")
watch=[]
if variation!="Same process in first-wave departments":watch.append(["Department variation","Managers describe different rules or exceptions for the same work.","Compare first-wave departments before copying a configuration.","Before configuration","Likely","Major"])
if labor=="Union or contract rules apply":watch.append(["Union and employment agreement requirements","The observed shift-bidding order, minimum rest period, overtime rule or approval process differs from the applicable agreement.","Review the specific requirement with Labor Relations and update the workflow before configuration.","While confirming operating rules","Possible","Major"])
if governance=="Department-level managers":watch.append(["Uneven local adoption","Departments continue using calls, texts or spreadsheets after testing.","Include department managers in observation, testing and issue review.","During testing and first launch","Possible","Moderate"])
if not watch:watch=[["Local workflow mismatch","The selected department behaves differently from the reported process.","Update the workflow and rules before complete testing.","During observation and testing","Possible","Moderate"]]
watch_columns=["Potential issue","Warning sign","Recommended response","Review point","Likelihood","Impact"]
saved_watch=loaded.get("potential_issues")
if saved_watch:
    normalized=[]
    for item in saved_watch:
        normalized.append([item.get("potential_issue",""),item.get("warning_sign",""),item.get("recommended_response",""),item.get("review_point",""),item.get("likelihood","Possible"),item.get("impact","Moderate")])
    watch=normalized
watch_df=pd.DataFrame(watch,columns=watch_columns)
watch_df=st.data_editor(watch_df,hide_index=True,width="stretch",num_rows="dynamic",key=f"flags:{choice}:{form_key}",column_config={"Potential issue":st.column_config.TextColumn(width="medium"),"Warning sign":st.column_config.TextColumn(width="large"),"Recommended response":st.column_config.TextColumn(width="large"),"Review point":st.column_config.TextColumn(width="medium"),"Likelihood":st.column_config.SelectboxColumn(options=["Unlikely","Possible","Likely"]),"Impact":st.column_config.SelectboxColumn(options=["Minor","Moderate","Major"])})
likelihood_score={"Unlikely":1,"Possible":2,"Likely":3};impact_score={"Minor":1,"Moderate":2,"Major":3}
watch_df["Score"]=watch_df["Likelihood"].map(likelihood_score).fillna(2)*watch_df["Impact"].map(impact_score).fillna(2)
watch_df["Priority"]=watch_df["Score"].apply(lambda value:"High" if value>=6 else "Medium" if value>=3 else "Low")
priority_view=watch_df.sort_values(["Score","Potential issue"],ascending=[False,True])[["Priority","Potential issue","Likelihood","Impact","Recommended response"]]
st.markdown("**Priority order**")
def color_priority(value):
    return {"High":"background-color:#f6dddd;color:#7b2424;font-weight:700","Medium":"background-color:#fff0c9;color:#765100;font-weight:700","Low":"background-color:#dcefe5;color:#155b39;font-weight:700"}.get(value,"")
st.dataframe(priority_view.style.map(color_priority,subset=["Priority"]),hide_index=True,width="stretch")
watch=watch_df.values.tolist()
st.header("5. Deployment decision brief")
states=required.Status.tolist()
if "Must wait" in states:readiness="Waiting on a required system"
elif any(s in states for s in ["Temporary route available","Connection required","Needs confirmation"]) or rules!="Documented and confirmed" or owner!="Named":readiness="Preparation required before complete testing"
else:readiness="Ready to set up the first-department workflow"
if "Temporary route available" in states:decision_needed="Approve a temporary information transfer for the first department or wait for the permanent source."
elif "Needs confirmation" in states:decision_needed="Confirm the unresolved information source and transfer method before approving the launch plan."
elif "Connection required" in states:decision_needed="Confirm who will prepare the required connection and agree its planning time."
elif owner!="Named":decision_needed="Name the hospital decision-maker for the first scope."
elif rules!="Documented and confirmed":decision_needed="Confirm the first department's operating rules before setup."
else:decision_needed="Proceed with first-department setup and complete workflow testing."
critical_package=timing.loc[timing["Recommended maximum weeks"].astype(float).idxmax(),"Work package"]
st.markdown(f"**Recommended first move**  \n{route}")
st.markdown(f"**Why this route**  \n{reason}")
st.markdown(f"**Current readiness**  \n{readiness}")
st.markdown(f"**Estimated timeline**  \n{total[0]:g}–{total[1]:g} weeks to first-department launch. The longest planned work package is {critical_package.lower()}.")
st.markdown("**Immediate priorities**")
for _,item in plan_df.head(3).iterrows():st.write(f'{int(item["Item"])}. {item["Action"]}')
st.warning(f"**Decision required:** {decision_needed}")
st.markdown("**Before expanding**  \nConfirm that the department is using the workflow as intended, resolve important incidents and compare the agreed result with the pre-launch baseline.")

st.header("6. Download working files")
safe_department=re.sub(r"[^a-z0-9]+","_",department.lower()).strip("_") or "department"
assessment={"selection":choice,"scope":{"solution":solution,"capabilities":capabilities,"department":department,"staff_groups":staff,"hospitals":sites},"hospital_context":{"type":profile,"current_owner":governance,"process_variation":variation,"manual_work":manual,"exceptions":exceptions,"rules":rules,"labor_rules":labor,"decision_owner":owner,"approvers":approvers},"recommended_rollout":{"route":route,"reason":reason,"main_dependency":critical_text,"estimated_timeline_weeks":{"minimum":total[0],"maximum":total[1]}},"information_dependencies":df.to_dict("records"),"action_plan":plan_df.to_dict("records"),"timeline":timing.to_dict("records"),"effort_estimate":effort.to_dict("records"),"expansion_estimate":{"departments":next_departments,"hospitals":next_hospitals,"reuse":reuse,"minimum_weeks":wave_min,"maximum_weeks":wave_max},"potential_issues":[{"potential_issue":r["Potential issue"],"warning_sign":r["Warning sign"],"recommended_response":r["Recommended response"],"review_point":r["Review point"],"likelihood":r["Likelihood"],"impact":r["Impact"],"priority":r["Priority"]} for _,r in watch_df.iterrows()]}
e1,e2,e3,e4=st.columns(4)
e1.download_button("Download action plan",plan_df.to_csv(index=False),f"hospital_deployment_action_plan_{safe_department}.csv","text/csv")
e2.download_button("Download dependencies",df.to_csv(index=False),f"hospital_deployment_dependencies_{safe_department}.csv","text/csv")
e3.download_button("Download timeline",timing.to_csv(index=False),f"hospital_deployment_timeline_{safe_department}.csv","text/csv")
e4.download_button("Download full assessment",json.dumps(assessment,indent=2,default=str),f"hospital_deployment_assessment_{safe_department}.json","application/json")
with st.expander("Method and limitations"):
    st.write("Hospital characteristics generate planning assumptions to test, not confirmed problems. Public cases inform common patterns but do not establish a vendor's internal process or exact deployment duration.")
