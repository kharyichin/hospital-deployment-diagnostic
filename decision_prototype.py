import json
import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Vitalize Deployment Planning Diagnostic",layout="wide")
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
    if "Must wait" in s:return "Wait for the required source system","A required information path is unavailable and no temporary route is accepted."
    if "Temporary route available" in s:return "Prepare the first department while deciding whether to use a temporary information transfer","A changing source system controls complete testing, but an interim route may support the first department."
    if "Needs confirmation" in s:return "Complete the unresolved assessment before committing to the launch plan","At least one required source, transfer or owner has not been confirmed."
    if "Connection required" in s:return "Prepare the first department while the required connection is built","Rules and connection work can proceed together. Complete testing waits for both."
    if rules!="Documented and confirmed":return "Reuse existing information paths while local rules are confirmed","Technical paths are usable, but configuration depends on confirmed operating rules."
    if owner!="Named":return "Name the hospital decision owner before configuration","Information paths are ready, but decisions have no accountable owner."
    return "Reuse the existing setup for a controlled first-department launch","Required information paths, rules and ownership are reported as ready."

st.title("Vitalize Deployment Planning Diagnostic")
st.write("Assess the proposed rollout, identify what controls the first launch, and build a practical hospital-specific plan.")
choice=st.selectbox("Current selection",list(EXAMPLES),index=1)
st.caption("Examples use a fictional ICU rollout. Change any answer to see how the plan changes.")
if st.button("Reset this selection"):
    for key in list(st.session_state):
        if choice in str(key): del st.session_state[key]
    st.rerun()
profile0,governance0,rules0,owner0=EXAMPLES[choice]

st.header("1. Hospital and rollout assessment")
st.info("Answers reflect the information available today. Record how each system answer was checked, then verify the workflow with the responsible hospital teams during discovery.")
a,b,c,d=st.tabs(["Scope of work","Current process","Rules and ownership","Systems and information"])
with a:
    x,y=st.columns(2)
    solution=x.selectbox("Vitalize solution in scope",list(SOLUTIONS)); capabilities=x.multiselect("Capabilities included in the first rollout",SOLUTIONS[solution],default=SOLUTIONS[solution][:2])
    department=y.text_input("First ward or department",value="ICU"); staff=y.multiselect("Staff groups included",["Nurses","Nurse managers","Central staffing team","Allied health","Physicians or advanced practice providers","Hospital executives","Other"],default=["Nurses","Nurse managers","Central staffing team"]); sites=y.number_input("Hospitals included in the first rollout",1,value=1)
with b:
    x,y=st.columns(2)
    profiles=["Not selected","Academic medical center","Multi-hospital regional system","Community or rural hospital"]
    profile=x.selectbox("Hospital type",profiles,index=profiles.index(profile0)); governance=x.selectbox("Who currently manages this work?",["Central staffing team","Department-level managers","Shared between central and department teams","Not confirmed"],index=["Central staffing team","Department-level managers","Shared between central and department teams","Not confirmed"].index(governance0))
    manual=y.multiselect("How is this work completed today?",["Workforce software","Spreadsheets","Calls or texts","Paper forms","Manual entry between systems","None identified","Not confirmed"],default=["None identified"] if choice==list(EXAMPLES)[1] else ["Spreadsheets"]); variation=y.selectbox("Does the process differ between departments?",["Same process in first-wave departments","Some local differences","Process differs by department","Not confirmed"]); exceptions=y.multiselect("Which situations regularly require manual decisions?",["Sick calls","Vacant shifts","Shift swaps","Overtime approval","Float staff","Staff reassignment","Downtime or connection failure","Not confirmed"],default=["Vacant shifts"])
with c:
    x,y=st.columns(2); rule_options=["Documented and confirmed","Written, but some rules need confirmation","Used in practice but not fully documented","Not documented","Not confirmed"]
    rules=x.selectbox("How are the current operating rules recorded?",rule_options,index=rule_options.index(rules0)); labor=x.selectbox("Do union or employment-contract rules apply?",["Union or contract rules apply","No union or contract rules identified","Not confirmed"])
    owner=y.selectbox("Is a hospital decision-maker named for this scope?",["Named","Not named","Not confirmed"],index=["Named","Not named","Not confirmed"].index(owner0)); approvers=y.multiselect("Who must approve changes to this workflow?",["Nursing operations","Department managers","Central staffing office","Hospital IT","HR or payroll","Labor Relations","Information security or privacy","Not confirmed"],default=["Nursing operations","Hospital IT"])
with d:
    default=ROWS.get(choice,[["Employee IDs and department assignments","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Qualifications and shift eligibility","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Patient demand and required coverage","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"]])
    raw=pd.DataFrame(default,columns=["Information needed","Source system","Source status","Transfer method","Required before first launch","Temporary route","How this was checked"])
    flows=st.data_editor(raw,hide_index=True,width="stretch",num_rows="dynamic",key=f"flows:{choice}",column_config={"Information needed":st.column_config.SelectboxColumn(options=INFO),"Source system":st.column_config.SelectboxColumn(options=SYSTEMS),"Source status":st.column_config.SelectboxColumn(options=["Available and stable","Being replaced","New system being introduced","Not available","Not confirmed"]),"Transfer method":st.column_config.SelectboxColumn(options=["Direct connection","Existing scheduled file","File upload","Manual entry","Same system","New connection required","Not confirmed"]),"Required before first launch":st.column_config.SelectboxColumn(options=["Yes","No"]),"Temporary route":st.column_config.SelectboxColumn(options=["Not needed","Allowed for first department","Not allowed","Not confirmed"]),"How this was checked":st.column_config.SelectboxColumn(options=["Reported by stakeholder","Document reviewed","Observed in practice","Tested successfully","Not confirmed"])})

df=flows.copy();df["Status"]=df.apply(status,axis=1); required=df[df["Required before first launch"]=="Yes"]
route,reason=recommend(df,rules,owner); critical=required[required.Status.isin(["Must wait","Temporary route available","Connection required","Needs confirmation"])]
critical_text="No controlling dependency identified" if critical.empty else f'{critical.iloc[0]["Information needed"]} from {critical.iloc[0]["Source system"]}'

st.header("2. Recommended rollout plan");st.info(route);st.write(reason)
m1,m2,m3=st.columns(3)
m1.metric("Recommended first scope",department,delta=f"{len(capabilities)} capabilities included",delta_color="off")
m2.metric("Required information paths ready",f'{int((required.Status=="Ready").sum())} of {len(required)}')
m3.metric("Unresolved required paths",len(critical))
m3.caption(f"Main dependency: {critical_text}")
st.subheader("Deployment summary")
system_names=[x for x in required["Source system"].dropna().unique().tolist() if x!="Not confirmed"]
systems_text=", ".join(system_names) if system_names else "the required source systems"
rule_setup={"Workforce management":f"Enter the {department} scheduling and approval rules.","Flow and capacity operations":f"Enter the {department} flow, capacity and escalation rules.","Executive analytics":f"Enter the {department} alert, reporting and escalation rules."}[solution]
st.write(f"Before testing, the team needs to make the selected {department} workflow work inside Vitalize:")
st.markdown(f"1. Add the {department} staff who will use it.\n2. {rule_setup}\n3. Connect the required {systems_text} information.\n4. Give test users access.\n5. Prepare normal and exception scenarios to test.")
plan=[[1,"Observe the current workflow, exceptions and baseline for the selected scope.","Deployment team","Hospital operations and intended users","Start now"]]
if rules!="Documented and confirmed":plan.append([2,"Confirm the first department's operating rules and exceptions.","Deployment team","Department managers and Nursing operations"+("; Labor Relations" if labor=="Union or contract rules apply" else ""),"Do together with item 1"])
for _,r in critical.iterrows():plan.append([len(plan)+1,f'{r["Information needed"]}: resolve {r["Status"].lower()} for {r["Source system"]}.',"Source-system owner","Hospital IT and the deployment team",f'Do after item 1; complete before testing'])
plan.append([len(plan)+1,"Test normal work, exceptions and recovery from source information through the complete workflow.","Deployment team","Intended users and Hospital IT",f'Do after items 1–{len(plan)}'])
plan_df=pd.DataFrame(plan,columns=["Item","Action item","Owner","Supporting parties","Timing / status"])
plan_df=st.data_editor(plan_df,hide_index=True,width="stretch",disabled=["Item","Action item","Owner","Supporting parties"],key=f"plan:{choice}",column_config={"Timing / status":st.column_config.TextColumn(help="Examples: Do together with item 1; Do after item 2; Ongoing; Completed")})
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
st.write("Recommended planning time. Edit the ranges when hospital or Vitalize estimates are available.")
complexity=int(sites>1)+int(variation!="Same process in first-wave departments")+int(labor=="Union or contract rules apply")+int(profile=="Academic medical center"); connections=int(required.Status.isin(["Connection required","Temporary route available","Must wait","Needs confirmation"]).sum())
timing=pd.DataFrame([["Workflow discovery",1,2+min(complexity,2),"Access to department operators"],["Rule confirmation",1,1+(2 if rules!="Documented and confirmed" else 0)+(1 if labor=="Union or contract rules apply" else 0),"Observed workflow"],["Information and connection preparation",1,2+connections*2,"Confirmed sources, access and owners"],["Configuration and complete workflow testing",2,3,"Confirmed rules and usable information paths"],["User preparation and controlled launch",1,2,"Completed workflow testing"]],columns=["Work package","Recommended minimum weeks","Recommended maximum weeks","Must be completed first"])
timing=st.data_editor(timing,hide_index=True,width="stretch",disabled=["Work package","Must be completed first"],key=f"time:{choice}")
vals=[(float(r.iloc[1]),float(r.iloc[2])) for _,r in timing.iterrows()]; starts=[(0,0),vals[0],vals[0],(vals[0][0]+max(vals[1][0],vals[2][0]),vals[0][1]+max(vals[1][1],vals[2][1])),(0,0)];starts[4]=(starts[3][0]+vals[3][0],starts[3][1]+vals[3][1]);total=(starts[4][0]+vals[4][0],starts[4][1]+vals[4][1])
st.metric("Estimated time to first-department launch",f"{total[0]:g}–{total[1]:g} weeks")
fig=go.Figure(); colors=["#177e89","#4d8f7f","#d08a33","#635b8f","#2b6e7d"]
for i,r in timing.iterrows():fig.add_trace(go.Bar(name=r["Work package"],y=["Recommended plan"],x=[r["Recommended maximum weeks"]],base=[starts[i][1]],orientation="h",marker_color=colors[i],text=f'Week {int(starts[i][1])+1}–{int(starts[i][1]+r["Recommended maximum weeks"])}',textposition="inside"))
fig.update_layout(barmode="overlay",xaxis_title="Week",xaxis=dict(dtick=1),height=240,margin=dict(l=0,r=0,t=10,b=0));st.plotly_chart(fig,width="stretch")
st.caption("Rule confirmation and information preparation occupy the same weeks. Testing starts after both are complete. All ranges are editable planning assumptions.")

st.header("4. Potential issues and flags")
watch=[]
if variation!="Same process in first-wave departments":watch.append(["Department variation","Managers describe different rules or exceptions for the same work.","Compare first-wave departments before copying a configuration.","Before configuration"])
if labor=="Union or contract rules apply":watch.append(["Union and employment agreement requirements","The observed shift-bidding order, minimum rest period, overtime rule or approval process differs from the applicable agreement.","Review the specific requirement with Labor Relations and update the workflow before configuration.","While confirming operating rules"])
if governance=="Department-level managers":watch.append(["Uneven local adoption","Departments continue using calls, texts or spreadsheets after testing.","Include department managers in observation, testing and issue review.","During testing and first launch"])
if not watch:watch=[["Local workflow mismatch","The selected department behaves differently from the reported process.","Update the workflow and rules before complete testing.","During observation and testing"]]
watch_df=pd.DataFrame(watch,columns=["Potential issue","Warning sign","Recommended response","Review point"])
watch_df=st.data_editor(watch_df,hide_index=True,width="stretch",num_rows="dynamic",key=f"flags:{choice}",column_config={"Potential issue":st.column_config.TextColumn(width="medium"),"Warning sign":st.column_config.TextColumn(width="large"),"Recommended response":st.column_config.TextColumn(width="large"),"Review point":st.column_config.TextColumn(width="medium")})
watch=watch_df.values.tolist()
with st.expander("First 14 days of fieldwork",expanded=True):
    tasks=[("Days 1–3",f"Observe how {department} completes the selected work, including handoffs and frequent exceptions."),("Days 1–3","Record spreadsheets, calls, texts, paper forms and manual entry used alongside current systems."),("Days 4–7","Confirm the operating rules and name the people who can approve changes and exceptions."),("Days 8–10","Confirm each required information source, transfer method and available alternative."),("Days 11–14","Agree the recommended first scope, estimated timeline and complete-testing requirements.")]
    if labor=="Union or contract rules apply":tasks.insert(3,("Days 4–7","Review the contract provisions that affect the selected workflow with Labor Relations."))
    if governance=="Department-level managers":tasks.insert(2,("Days 1–7","Include department managers from each shift in workflow observation and review."))
    done=0
    safe_choice=re.sub(r"[^a-z0-9]+","_",choice.lower())
    for i,(period,task) in enumerate(tasks):
        if st.checkbox(f"{period}: {task}",key=f"fieldwork:{safe_choice}:{i}"):done+=1
    st.progress(done/len(tasks));st.caption(f"{done} of {len(tasks)} fieldwork items completed")

st.header("5. Deployment decision brief")
states=required.Status.tolist()
if "Must wait" in states:readiness="Waiting on a required system"
elif any(s in states for s in ["Temporary route available","Connection required","Needs confirmation"]) or rules!="Documented and confirmed" or owner!="Named":readiness="Preparation required before complete testing"
else:readiness="Ready to set up the first-department workflow"
if "Temporary route available" in states:decision_needed="Approve a temporary information transfer for the first department or wait for the permanent source."
elif "Needs confirmation" in states:decision_needed="Confirm the unresolved information path before approving the launch plan."
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
for _,item in plan_df.head(3).iterrows():st.write(f'{int(item["Item"])}. {item["Action item"]}')
st.warning(f"**Decision required:** {decision_needed}")
st.markdown("**Before expanding**  \nConfirm that the department is using the workflow as intended, resolve important incidents and compare the agreed result with the pre-launch baseline.")

st.header("6. Download working files")
safe_department=re.sub(r"[^a-z0-9]+","_",department.lower()).strip("_") or "department"
assessment={"selection":choice,"scope":{"solution":solution,"capabilities":capabilities,"department":department,"staff_groups":staff,"hospitals":sites},"hospital_context":{"type":profile,"current_owner":governance,"process_variation":variation,"manual_work":manual,"exceptions":exceptions,"rules":rules,"labor_rules":labor,"decision_owner":owner,"approvers":approvers},"recommended_rollout":{"route":route,"reason":reason,"main_dependency":critical_text,"estimated_timeline_weeks":{"minimum":total[0],"maximum":total[1]}},"information_dependencies":df.to_dict("records"),"action_plan":plan_df.to_dict("records"),"timeline":timing.to_dict("records"),"potential_issues":[dict(zip(["potential_issue","warning_sign","recommended_response","review_point"],row)) for row in watch]}
e1,e2,e3,e4=st.columns(4)
e1.download_button("Download action plan",plan_df.to_csv(index=False),f"vitalize_action_plan_{safe_department}.csv","text/csv")
e2.download_button("Download dependencies",df.to_csv(index=False),f"vitalize_dependencies_{safe_department}.csv","text/csv")
e3.download_button("Download timeline",timing.to_csv(index=False),f"vitalize_timeline_{safe_department}.csv","text/csv")
e4.download_button("Download full assessment",json.dumps(assessment,indent=2,default=str),f"vitalize_assessment_{safe_department}.json","application/json")
with st.expander("Method and limitations"):
    st.write("Hospital characteristics generate planning assumptions to test, not confirmed problems. Public cases inform common patterns but do not establish Vitalize's internal process or exact deployment duration.")
