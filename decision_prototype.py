import json
import re
import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Hospital Deployment Planning Diagnostic",layout="wide")
st.markdown("<style>.block-container{max-width:1280px;padding-top:2rem}h1,h2,h3{letter-spacing:-.025em}[data-testid='stMetric']{background:#f4f8f7;border:1px solid #d6e3df;padding:14px;border-radius:8px}.ready-group{border-left:4px solid var(--group);background:var(--tint);padding:10px 12px;margin:8px 0;border-radius:4px}.ready-group strong{color:var(--text);display:block;margin-bottom:5px}.ready-item{color:#24343b;line-height:1.45;margin:2px 0}.ready-item span{color:var(--text);font-weight:700;margin-right:6px}</style>",unsafe_allow_html=True)

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
SCOPE_QUESTIONS={
    "Workforce management":{
        "method":("How are schedules and open shifts managed today?",["One central staffing process","Each department manages its own","Shared between central and department teams","Not confirmed"]),
        "decision":("What determines who can take a shift?",["Qualifications and availability","Qualifications, availability and employment rules","Manager judgement","Not confirmed"]),
        "manual":("Which parts still require manual follow-up?",["Collecting availability","Checking qualifications","Contacting staff about open shifts","Approving swaps or overtime","Correcting time or pay codes","None identified","Not confirmed"]),
    },
    "Flow and capacity operations":{
        "method":("How are changes in patient demand and capacity identified?",["Live operational system","Shift handovers or operational huddles","Spreadsheets, calls or messages","Not confirmed"]),
        "decision":("How often must capacity information be updated?",["Continuously or near real time","At each shift change","Daily","Not confirmed"]),
        "manual":("Which parts still require manual coordination?",["Confirming available beds","Confirming expected discharges","Escalating capacity constraints","Matching staffing to demand","None identified","Not confirmed"]),
    },
    "Executive analytics":{
        "method":("How are staffing and capacity reports produced today?",["Automatically from shared systems","Combined manually from several systems","Each department produces its own reports","Not confirmed"]),
        "decision":("Are the reported measures defined the same way across departments?",["Yes, the definitions are shared","Some definitions differ","Definitions differ substantially","Not confirmed"]),
        "manual":("Which parts still require manual work?",["Collecting data","Reconciling conflicting figures","Producing reports","Following up on alerts","None identified","Not confirmed"]),
    },
}
INFO=["Employee IDs and department assignments","Qualifications and shift eligibility","Availability and approved leave","Existing rosters and vacant shifts","Patient demand and required coverage","Actual worked hours","Payroll codes"]
SYSTEMS=["Workday","Oracle PeopleSoft","Oracle Fusion Cloud HCM","UKG Pro WFM / Dimensions","UKG Workforce Central / Kronos","QGenda","symplr Smart Square","M7","Epic","MEDITECH","Spreadsheet or paper","Other","Not confirmed"]
PLATFORM_ITEMS=[
    ("Department setup", "Has the first ward or department been created in the platform?"),
    ("Users and access", "Have the staff, managers and access levels for the first rollout been set up?"),
    ("Operating rules", "Have the approved scheduling, approval and exception rules been entered?"),
    ("Data mapping", "Have the required hospital fields been matched to the correct platform fields?"),
    ("Test setup", "Are test users, sample data and normal and exception scenarios ready?"),
]
PLATFORM_STATUS=["Not checked","Not started","In progress","Ready and checked"]

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
    ("Complete the assessment","Record the hospital conditions and confirm what must be prepared inside the platform.","1-assess-the-rollout"),
    ("Review the deployment plan","See the recommended route, internal playbook steps and case-specific actions.","2-deployment-plan"),
    ("Save the case","Download the case record or action tracker for the team.","5-case-summary-and-exports"),
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

st.header("1. Assess the rollout")
st.info("Answers reflect the information available today. Record how each system answer was checked, then verify the workflow with the responsible hospital teams during discovery.")
a,b,c,d,e=st.tabs(["1. Scope of work","2. Current process","3. Rules and ownership","4. Systems and information","5. Platform preparation"])
with a:
    x,y=st.columns(2)
    solution_options=list(SOLUTIONS);solution_default=loaded_scope.get("solution") if loaded_scope.get("solution") in solution_options else solution_options[0]
    solution=x.selectbox("Deployment scope",solution_options,index=solution_options.index(solution_default),key=f"solution:{form_key}",help="Choose the hospital workflow this assessment will plan. Keep the first rollout narrow enough to test completely.")
    loaded_capabilities=[item for item in loaded_scope.get("capabilities",[]) if item in SOLUTIONS[solution]]
    capabilities=x.multiselect("Capabilities included in the first rollout",SOLUTIONS[solution],default=loaded_capabilities or SOLUTIONS[solution][:2],key=f"capabilities:{form_key}",help="Select only the capabilities intended for the first ward, department or hospital.")
    department=y.text_input("Name of first ward or department",value=loaded_scope.get("department","ICU"),key=f"department:{form_key}")
    default_case_name=f'{department or "First department"} {solution.lower()} rollout'
    case_name=y.text_input("Case name",value=loaded.get("case_name",default_case_name),key=f"case_name:{form_key}",help="Use a name the deployment team can recognise later.")
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
    variation_details=""
    if variation in ["Some local differences","Process differs by department"]:
        variation_details=y.text_area(
            "What differs between departments?",
            value=loaded_context.get("process_variation_details",""),
            placeholder="Example: ICU shift swaps require charge-nurse approval, while medical wards allow manager approval.",
            key=f"variation_details:{form_key}",
        )
    exception_options={
        "Workforce management":["Sick calls","Vacant shifts","Shift swaps","Overtime approval","Float staff","Staff reassignment","Downtime or connection failure","Not confirmed"],
        "Flow and capacity operations":["Unexpected demand surge","Delayed discharge","Bed unavailable","Staffing does not match demand","Patient-transfer delay","Downtime or connection failure","Not confirmed"],
        "Executive analytics":["Conflicting figures","Delayed report","Alert has no assigned owner","Hospital or department cannot be compared","Missing source data","Not confirmed"],
    }[solution]
    exception_default=["Vacant shifts"] if solution=="Workforce management" else [exception_options[0]]
    exceptions=y.multiselect("Which situations regularly require manual decisions?",exception_options,default=[item for item in loaded_context.get("exceptions",exception_default) if item in exception_options],key=f"exceptions:{solution}:{form_key}")
    st.markdown(f"**Questions for {solution.lower()}**")
    scope_questions=SCOPE_QUESTIONS[solution]
    scope_method_options=scope_questions["method"][1]
    scope_method_default=loaded_context.get("scope_method",scope_method_options[0] if choice==list(EXAMPLES)[1] else scope_method_options[-1])
    scope_method=st.selectbox(scope_questions["method"][0],scope_method_options,index=scope_method_options.index(scope_method_default) if scope_method_default in scope_method_options else len(scope_method_options)-1,key=f"scope_method:{solution}:{form_key}")
    scope_decision_options=scope_questions["decision"][1]
    scope_decision_default=loaded_context.get("scope_decision",scope_decision_options[0] if choice==list(EXAMPLES)[1] else scope_decision_options[-1])
    scope_decision=st.selectbox(scope_questions["decision"][0],scope_decision_options,index=scope_decision_options.index(scope_decision_default) if scope_decision_default in scope_decision_options else len(scope_decision_options)-1,key=f"scope_decision:{solution}:{form_key}")
    scope_manual_options=scope_questions["manual"][1]
    scope_manual_default=[item for item in loaded_context.get("scope_manual",["None identified"] if choice==list(EXAMPLES)[1] else [scope_manual_options[-1]]) if item in scope_manual_options]
    scope_manual=st.multiselect(scope_questions["manual"][0],scope_manual_options,default=scope_manual_default,key=f"scope_manual:{solution}:{form_key}")
with c:
    x,y=st.columns(2); rule_options=["Documented and confirmed","Written, but some rules need confirmation","Used in practice but not fully documented","Not documented","Not confirmed"]
    rules_default=loaded_context.get("rules",rules0);rules=x.selectbox("How are the current operating rules recorded?",rule_options,index=rule_options.index(rules_default) if rules_default in rule_options else 4,key=f"rules:{form_key}")
    labor_options=["Union or contract rules apply","No union or contract rules identified","Not confirmed"];labor_default=loaded_context.get("labor_rules",labor_options[0])
    labor=x.selectbox("Do union or employment-contract rules apply?",labor_options,index=labor_options.index(labor_default) if labor_default in labor_options else 2,key=f"labor:{form_key}")
    labor_groups=[];labor_requirements=[];labor_confirmation="Not required"
    if labor=="Union or contract rules apply":
        labor_group_options=["Nurses","Allied health","Physicians or advanced practice providers","Other staff groups","Not confirmed"]
        labor_groups=x.multiselect("Which staff groups are covered?",labor_group_options,default=[item for item in loaded_context.get("labor_groups",["Nurses"] if choice==list(EXAMPLES)[1] else ["Not confirmed"]) if item in labor_group_options],key=f"labor_groups:{form_key}")
        labor_requirement_options=["Shift bidding or seniority","Minimum rest periods","Overtime","Shift swaps","Reassignment between departments","Other","Not confirmed"]
        labor_requirements=x.multiselect("Which parts of the workflow are affected?",labor_requirement_options,default=[item for item in loaded_context.get("labor_requirements",["Shift bidding or seniority","Overtime"] if choice==list(EXAMPLES)[1] else ["Not confirmed"]) if item in labor_requirement_options],key=f"labor_requirements:{form_key}")
        labor_confirmation_options=["Confirmed with Labor Relations","Needs confirmation","Not confirmed"]
        labor_confirmation_default=loaded_context.get("labor_confirmation",labor_confirmation_options[0] if choice==list(EXAMPLES)[1] else labor_confirmation_options[-1])
        labor_confirmation=x.selectbox("Have these requirements been confirmed?",labor_confirmation_options,index=labor_confirmation_options.index(labor_confirmation_default) if labor_confirmation_default in labor_confirmation_options else 2,key=f"labor_confirmation:{form_key}")
    owner_options=["Named","Not named","Not confirmed"];owner_default=loaded_context.get("decision_owner",owner0)
    owner=y.selectbox("Is a hospital decision-maker named for this scope?",owner_options,index=owner_options.index(owner_default) if owner_default in owner_options else 2,key=f"owner:{form_key}")
    approver_options=["Nursing operations","Department managers","Central staffing office","Hospital IT","HR or payroll","Labor Relations","Information security or privacy","Not confirmed"]
    approvers=y.multiselect("Who must approve changes to this workflow?",approver_options,default=[item for item in loaded_context.get("approvers",["Nursing operations","Hospital IT"]) if item in approver_options],key=f"approvers:{form_key}")
with d:
    columns=["Information needed","Source system","Source status","Transfer method","Required before first launch","Temporary route","How this was checked"]
    default=loaded.get("information_dependencies") or ROWS.get(choice,[["Employee IDs and department assignments","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Qualifications and shift eligibility","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"],["Patient demand and required coverage","Not confirmed","Not confirmed","Not confirmed","Yes","Not confirmed","Not confirmed"]])
    raw=pd.DataFrame(default);raw=raw[columns] if set(columns).issubset(raw.columns) else pd.DataFrame(default,columns=columns)
    flows=st.data_editor(raw,hide_index=True,width="stretch",num_rows="dynamic",key=f"flows:{choice}:{form_key}",column_config={"Information needed":st.column_config.SelectboxColumn(options=INFO),"Source system":st.column_config.SelectboxColumn(options=SYSTEMS),"Source status":st.column_config.SelectboxColumn(options=["Available and stable","Being replaced","New system being introduced","Not available","Not confirmed"]),"Transfer method":st.column_config.SelectboxColumn(options=["Direct connection","Existing scheduled file","File upload","Manual entry","Same system","New connection required","Not confirmed"]),"Required before first launch":st.column_config.SelectboxColumn(options=["Yes","No"]),"Temporary route":st.column_config.SelectboxColumn(options=["Not needed","Allowed for first department","Not allowed","Not confirmed"]),"How this was checked":st.column_config.SelectboxColumn(options=["Reported by stakeholder","Document reviewed","Observed in practice","Tested successfully","Not confirmed"])})
with e:
    st.write("Confirm what has been prepared inside the platform for the first rollout.")
    saved_platform={(item.get("Item") or item.get("item")):(item.get("Status") or item.get("status")) for item in loaded.get("platform_preparation",[]) if isinstance(item,dict)}
    platform_rows=[]
    for item,question in PLATFORM_ITEMS:
        default_status=saved_platform.get(item,"Ready and checked" if choice==list(EXAMPLES)[1] else "Not checked")
        selected=st.selectbox(question,PLATFORM_STATUS,index=PLATFORM_STATUS.index(default_status) if default_status in PLATFORM_STATUS else 0,key=f"platform:{item}:{choice}:{form_key}")
        platform_rows.append({"Item":item,"Question":question,"Status":selected})
    st.caption("These are general software-deployment checks. Replace them with the company’s internal setup process when it is available.")

df=flows.copy();df["Status"]=df.apply(status,axis=1); required=df[df["Required before first launch"]=="Yes"]
platform_df=pd.DataFrame(platform_rows)
platform_open=platform_df[platform_df["Status"]!="Ready and checked"]
route,reason=recommend(df,rules,owner); critical=required[required.Status.isin(["Must wait","Temporary route available","Connection required","Needs confirmation"])]
critical_text="None" if critical.empty else f'{critical.iloc[0]["Information needed"]} from {critical.iloc[0]["Source system"]}'
scope_unknown=scope_method=="Not confirmed" or scope_decision=="Not confirmed" or "Not confirmed" in scope_manual
scope_manual_work=[item for item in scope_manual if item not in ["None identified","Not confirmed"]]
labor_work=labor=="Union or contract rules apply" and (labor_confirmation!="Confirmed with Labor Relations" or "Not confirmed" in labor_groups or "Not confirmed" in labor_requirements)
items_to_resolve=len(critical)+int(rules!="Documented and confirmed")+int(owner!="Named")+len(platform_open)+int(scope_unknown)+int(labor_work)

st.header("2. Deployment plan")
st.subheader("Recommended route")
ready_required=required[required.Status=="Ready"]
ready_details=[f'{r["Information needed"]} — {r["Source system"]}, {r["Transfer method"].lower()}' for _,r in ready_required.iterrows()]
ready_systems=[item for item in ready_required["Source system"].dropna().unique().tolist() if item!="Not confirmed"]
selected_tasks=[item.lower() for item in capabilities]
task_text=", ".join(selected_tasks[:-1])+(" and "+selected_tasks[-1] if len(selected_tasks)>1 else selected_tasks[0] if selected_tasks else "the selected tasks")
hospital_ready=critical.empty and rules=="Documented and confirmed" and owner=="Named" and not scope_unknown and not labor_work
testing_ready=hospital_ready and platform_open.empty
if testing_ready:
    system_text=", ".join(ready_systems[:-1])+(" and "+ready_systems[-1] if len(ready_systems)>1 else ready_systems[0] if ready_systems else "the confirmed source systems")
    recommended_next_move=f"Run end-to-end tests for {task_text} in {department} using information from {system_text}."
    playbook_name="Existing systems: first-department setup and testing"
elif not critical.empty:
    first_issue=critical.iloc[0];info_name=first_issue["Information needed"].lower();source_name=first_issue["Source system"]
    if first_issue["Status"]=="Must wait":recommended_next_move=f"Pause complete testing until {info_name} from {source_name} is available or another source is approved."
    elif first_issue["Status"]=="Temporary route available":recommended_next_move=f"Prepare the selected {department} tasks, then approve and test a temporary transfer of {info_name} from {source_name}."
    elif first_issue["Status"]=="Connection required":recommended_next_move=f"Prepare the selected {department} tasks while Hospital IT builds and tests the {source_name} connection for {info_name}."
    else:recommended_next_move=f"Confirm how {info_name} will be supplied from {source_name} before scheduling complete testing."
    playbook_name={"Must wait":"Unavailable source system","Temporary route available":"Temporary information transfer","Connection required":"New system connection","Needs confirmation":"Information source confirmation"}[first_issue["Status"]]
elif rules!="Documented and confirmed":
    recommended_next_move=f"Confirm the operating rules and exceptions for {task_text} in {department} before setup begins."
    playbook_name="Operating-rule confirmation"
elif owner!="Named":
    recommended_next_move="Name the hospital decision-maker before configuration begins."
    playbook_name="Decision ownership"
elif scope_unknown:
    recommended_next_move=f"Confirm how {solution.lower()} works today in {department} before finalising the rollout plan."
    playbook_name=f"{solution}: workflow discovery"
    reason="The selected workflow is not sufficiently confirmed to define its configuration and test scenarios."
elif labor_work:
    recommended_next_move="Confirm the employment requirements that affect the selected workflow before configuration begins."
    playbook_name="Employment-rule confirmation"
    reason="Employment requirements affect the workflow, but the covered groups or applicable rules are not fully confirmed."
elif not platform_open.empty:
    first_platform=platform_open.iloc[0]
    recommended_next_move=f'Complete the platform preparation for {department}. Start with: {first_platform["Item"].lower()}.'
    playbook_name=f'Platform preparation: {first_platform["Item"].lower()}'
else:
    recommended_next_move=f"Complete the remaining preparation for {task_text} in {department}."
    playbook_name=f"{solution}: first-department preparation"
with st.container(border=True):
    st.markdown("**Recommended next move**")
    st.subheader(recommended_next_move)
m1,m2,m3=st.columns(3)
m1.metric("Can end-to-end testing start?","Yes" if testing_ready else "Not yet")
m2.metric("Required information reported ready",f'{len(ready_required)} of {len(required)}')
m3.metric("Items to resolve before complete testing",items_to_resolve)

resolve=[]
if owner!="Named":resolve.append("Name the hospital decision-maker for this rollout.")
if rules!="Documented and confirmed":resolve.append("Confirm the operating rules and exceptions used by the first department.")
if scope_unknown:resolve.append(f"Confirm the unanswered questions about how {solution.lower()} works today.")
if labor_work:resolve.append("Confirm the covered staff groups and employment requirements with Labor Relations.")
for _,r in critical.iterrows():
    issue_text={"Needs confirmation":"the source or transfer method has not been confirmed","Connection required":"a new connection must be built and tested","Temporary route available":"the source system is changing, but a temporary transfer may be used","Must wait":"the information is unavailable and no alternative has been approved"}[r["Status"]]
    resolve.append(f'{r["Information needed"]} from {r["Source system"]}: {issue_text}.')
for _,r in platform_open.iterrows():
    resolve.append(f'{r["Item"]}: {r["Status"].lower()}.')
ready_groups={
    "Governance":{"colors":["#7452A3","#F1ECF7","#493269"],"items":[]},
    "Workflow and rules":{"colors":["#B36B00","#FFF3DC","#704300"],"items":[]},
    "Information connections":{"colors":["#287C9B","#E8F4F8","#18556C"],"items":ready_details.copy()},
    "Platform setup":{"colors":["#27805A","#E7F4ED","#18563D"],"items":[]},
}
if owner=="Named":ready_groups["Governance"]["items"].append("Hospital decision-maker named")
if rules=="Documented and confirmed":ready_groups["Workflow and rules"]["items"].append("Operating rules and exceptions confirmed")
if not scope_unknown:ready_groups["Workflow and rules"]["items"].append(f"Current {solution.lower()} workflow described")
if labor=="No union or contract rules identified" or labor_confirmation=="Confirmed with Labor Relations":ready_groups["Workflow and rules"]["items"].append("Employment-rule requirements confirmed")
for _,r in platform_df[platform_df["Status"]=="Ready and checked"].iterrows():ready_groups["Platform setup"]["items"].append(f'{r["Item"]} ready and checked')
left,right=st.columns(2,gap="large")
with left.container(border=True):
    st.markdown("**Confirmed and ready**")
    populated_groups={name:group for name,group in ready_groups.items() if group["items"]}
    if populated_groups:
        for name,group in populated_groups.items():
            accent,tint,text_color=group["colors"]
            items="".join(f'<div class="ready-item"><span>✓</span>{html.escape(str(item))}</div>' for item in group["items"])
            st.markdown(f'<div class="ready-group" style="--group:{accent};--tint:{tint};--text:{text_color}"><strong>{html.escape(name)}</strong>{items}</div>',unsafe_allow_html=True)
    else:st.write("Nothing has been confirmed as ready.")
with right.container(border=True):
    st.markdown("**Needs attention before complete testing**")
    if resolve:
        for item in resolve:st.write(f"• {item}")
    else:st.write("No outstanding items identified from the current answers.")

with st.container(border=True):
    st.subheader("Internal playbook to apply")
    saved_playbook=loaded.get("internal_playbook",{})
    playbook_reference=st.text_input("Internal playbook name",value=saved_playbook.get("reference",playbook_name),key=f"playbook_reference:{form_key}")
    playbook_url=st.text_input("Internal playbook link",value=saved_playbook.get("url",""),placeholder="https://...",key=f"playbook_url:{form_key}")
    st.caption("Connect this case to the company's approved instructions, templates and escalation process. The case tracker below records where this hospital needs a different approach.")
    p1,p2,p3=st.columns(3)
    p1.markdown("**1. Discover**  \nConfirm the current process, decisions, exceptions and baseline.")
    p2.markdown("**2. Align and prepare**  \nConfirm rules, information transfers and platform setup.")
    p3.markdown("**3. Test and launch**  \nTest normal and exception scenarios before the controlled launch.")
    if playbook_url.startswith(("https://","http://")):st.link_button("Open internal playbook",playbook_url)
    else:st.button("Open internal playbook",disabled=True,help="Add an internal playbook link to activate this button.")

plan=[[False,1,"Observe the current workflow, exceptions and baseline for the selected scope.","Every rollout needs an observed starting point before configuration.","Deployment team","Hospital operations and intended users","Days 1–3"]]
if sites>1:
    plan.append([False,len(plan)+1,"Compare the selected workflow across the hospitals in the first rollout.",f"The first rollout includes {int(sites)} hospitals. The same setup should only be reused where the workflow, rules and systems match.","Deployment team","Hospital operations and department managers","Do together with item 1"])
if variation in ["Some local differences","Process differs by department"]:
    difference_reason=variation_details.strip() or "The assessment reports differences between departments, but they have not been described yet."
    plan.append([False,len(plan)+1,"Compare the affected departments and document which rules, approvals and exceptions require a different setup.",difference_reason,"Deployment team","Department managers and intended users","Do together with item 1"])
if owner!="Named":plan.append([False,len(plan)+1,"Name the hospital decision-maker for the first rollout.","The assessment does not have a confirmed decision owner.","Hospital sponsor","Deployment team and department leadership","Days 1–3"])
if rules!="Documented and confirmed":plan.append([False,len(plan)+1,"Confirm the first department's operating rules and exceptions.",f'Current rules are recorded as: {rules.lower()}.' ,"Deployment team","Department managers and Nursing operations"+("; Labor Relations" if labor=="Union or contract rules apply" else ""),"Days 4–7"])
if scope_unknown:
    plan.append([False,len(plan)+1,f"Confirm how {solution.lower()} works today in {department}.","At least one scope-specific workflow answer is not confirmed.","Deployment team","Department operators and intended users","Do together with workflow observation"])
if scope_manual_work:
    plan.append([False,len(plan)+1,f"Map the manual steps for {', '.join(item.lower() for item in scope_manual_work)} and decide what the first rollout must replace or retain.","These parts of the selected workflow still require manual work.","Deployment team","Department operators and intended users","Complete before platform setup"])
if labor_work:
    affected=", ".join(item.lower() for item in labor_requirements if item!="Not confirmed") or "the affected employment requirements"
    plan.append([False,len(plan)+1,f"Confirm {affected} with Labor Relations before entering the rules in the platform.","Union or employment-contract requirements apply but have not been fully confirmed.","Hospital operations","Labor Relations and the deployment team","Complete before rule configuration"])
for _,r in critical.iterrows():
    if r["Status"]=="Needs confirmation":action=f'Confirm the source and transfer method for {r["Information needed"].lower()} from {r["Source system"]}.'
    elif r["Status"]=="Connection required":action=f'Build and test the transfer of {r["Information needed"].lower()} from {r["Source system"]}.'
    elif r["Status"]=="Temporary route available":action=f'Agree and test a temporary way to transfer {r["Information needed"].lower()} from {r["Source system"]}.'
    else:action=f'Confirm when {r["Information needed"].lower()} from {r["Source system"]} will be available, or approve another source.'
    plan.append([False,len(plan)+1,action,f'The assessment marked this information as: {r["Status"].lower()}.',"Source-system owner","Hospital IT and the deployment team","Days 4–10; complete before testing"])
platform_actions={
    "Department setup":f"Create the {department} structure and selected scope inside the platform.",
    "Users and access":f"Add the {department} users and confirm what each role can view, change and approve.",
    "Operating rules":f"Enter the confirmed {department} scheduling, approval and exception rules in the platform.",
    "Data mapping":"Match each required hospital field to its destination in the platform and resolve unmatched values.",
    "Test setup":"Prepare test users, sample data and normal, exception and recovery scenarios.",
}
for _,r in platform_open.iterrows():
    plan.append([False,len(plan)+1,platform_actions[r["Item"]],f'Platform preparation is marked as: {r["Status"].lower()}.',"Deployment team","Product or engineering and the relevant hospital team","Complete before end-to-end testing"])
plan.append([False,len(plan)+1,"Run normal, exception and recovery scenarios from the source systems through the platform and back to the responsible hospital team.","This confirms that the hospital process, information transfers and platform setup work together.","Deployment team","Intended users, Hospital IT and relevant product or engineering partners",f'Do after items 1–{len(plan)}'])
st.subheader("Case action tracker")
st.write("Use the standard playbook where it applies. Record what is different in this hospital and whether the standard playbook should change.")
plan_df=pd.DataFrame(plan,columns=["Done","Item","Action","Why this action appears","Owner","Supporting parties","Timing / status"])
def playbook_step(action):
    action=action.lower()
    if action.startswith("run normal, exception and recovery scenarios"):return "First-ward testing and launch"
    if any(word in action for word in ["observe","compare","confirm how","map the manual"]):return "Discovery"
    if any(word in action for word in ["rule","decision-maker","source","transfer","connection","create the","add the","enter the","match each","prepare test"]):return "System and rule alignment"
    return "First-ward testing and launch"
plan_df["Existing playbook step"]=plan_df["Action"].map(playbook_step)
plan_df["Case-specific difference"]=plan_df.apply(lambda row:"No case-specific difference identified." if row["Why this action appears"].startswith(("Every rollout","This confirms")) else row["Why this action appears"],axis=1)
plan_df["Status"]=plan_df["Done"].map({True:"Completed",False:"Not started"})
plan_df["Priority"]="Medium"
plan_df["Target date"]=""
plan_df["Evidence or link"]=""
plan_df["Playbook update needed?"]="Review after completion"
plan_columns=["Item","Action","Existing playbook step","Case-specific difference","Owner","Supporting parties","Status","Priority","Target date","Evidence or link","Playbook update needed?"]
plan_df=plan_df[plan_columns]
saved_plan=loaded.get("action_plan")
if saved_plan:
    saved_plan_df=pd.DataFrame(saved_plan)
    if set(plan_columns).issubset(saved_plan_df.columns):plan_df=saved_plan_df[plan_columns]
plan_df=st.data_editor(plan_df,hide_index=True,width="stretch",num_rows="dynamic",disabled=["Item","Action","Existing playbook step"],key=f"plan:{choice}:{form_key}",column_config={"Item":st.column_config.NumberColumn(width="small"),"Action":st.column_config.TextColumn(width="large"),"Existing playbook step":st.column_config.SelectboxColumn(options=["Discovery","System and rule alignment","First-ward testing and launch"]),"Case-specific difference":st.column_config.TextColumn(width="large"),"Status":st.column_config.SelectboxColumn(options=["Not started","Ongoing","Blocked","Completed"]),"Priority":st.column_config.SelectboxColumn(options=["High","Medium","Low"]),"Target date":st.column_config.TextColumn(help="Use the date format your team follows."),"Playbook update needed?":st.column_config.SelectboxColumn(options=["Review after completion","Hospital-specific only","Already covered","Add a new playbook step","Revise an existing playbook step","Product or engineering review"])})
completed=int((plan_df["Status"]=="Completed").sum())
open_actions=len(plan_df)-completed
st.markdown(f'<span style="display:inline-block;background:#dcefe5;color:#155b39;padding:4px 10px;border-radius:999px;font-weight:600">{completed} completed</span> <span style="display:inline-block;background:#e7eef5;color:#174e68;padding:4px 10px;border-radius:999px;font-weight:600">{open_actions} remaining</span>',unsafe_allow_html=True)
st.progress(completed/len(plan_df));st.caption(f"{completed} of {len(plan_df)} actions completed")
def color_status(value):
    colors={"Ready":"background-color:#dcefe5;color:#155b39;font-weight:600","Temporary route available":"background-color:#fff0c9;color:#765100;font-weight:600","Connection required":"background-color:#dcecf4;color:#174e68;font-weight:600","Needs confirmation":"background-color:#eceeef;color:#39434a","Must wait":"background-color:#f6dddd;color:#7b2424;font-weight:600"}
    return colors.get(value,"")
st.markdown("**Information and data gaps**")
dependency_view=df[df.Status!="Ready"][["Information needed","Source system","Source status","Transfer method","How this was checked","Status"]]
if dependency_view.empty:st.write("No information or data gaps identified.")
dependency_style=(dependency_view.style
    .map(color_status,subset=["Status"])
    .set_properties(**{"white-space":"normal","overflow-wrap":"anywhere"})
    .set_properties(subset=["Information needed"],**{"min-width":"230px"})
    .set_properties(subset=["How this was checked"],**{"min-width":"190px"})
    .set_properties(subset=["Status"],**{"min-width":"190px","white-space":"normal"}))
if not dependency_view.empty:st.dataframe(dependency_style,hide_index=True,width="stretch",height=min(420,80+len(dependency_view)*52))
with st.expander("Review all required information"):
    st.dataframe(df[["Information needed","Source system","Source status","Transfer method","How this was checked","Status"]],hide_index=True,width="stretch")

st.header("3. Timeline and team effort")
st.write("The estimate is calculated from the work generated by the assessment. Edit the ranges when hospital or vendor estimates are available.")
discovery_tasks=1+int(sites>1)+int(variation!="Same process in first-wave departments")+int(scope_unknown)+int(bool(scope_manual_work))
rule_tasks=int(rules!="Documented and confirmed")+int(labor_work)
connections=int(required.Status.isin(["Connection required","Temporary route available","Must wait","Needs confirmation"]).sum())
platform_work=max(1,len(platform_open))
forecast_drivers=[["Observe the selected workflow","Included for every rollout"]]
if sites>1:forecast_drivers.append(["Compare hospitals",f"The first rollout includes {int(sites)} hospitals"])
if variation!="Same process in first-wave departments":forecast_drivers.append(["Compare departments",f"Department variation is recorded as: {variation.lower()}"])
if scope_unknown:forecast_drivers.append(["Confirm the current workflow",f"At least one {solution.lower()} answer is not confirmed"])
if scope_manual_work:forecast_drivers.append(["Map manual handoffs",f'{len(scope_manual_work)} manual part(s) were identified'])
if rule_tasks:forecast_drivers.append(["Confirm operating or employment rules",f"{rule_tasks} rule-confirmation task(s) were generated"])
if connections:forecast_drivers.append(["Prepare information connections",f"{connections} required information path(s) need work"])
if len(platform_open):forecast_drivers.append(["Prepare the platform",f"{len(platform_open)} platform item(s) are not ready and checked"])
st.markdown("**Work included in this estimate**")
st.dataframe(pd.DataFrame(forecast_drivers,columns=["Generated work","Why it is included"]),hide_index=True,width="stretch")
timing=pd.DataFrame([["Workflow discovery",1,2+min(discovery_tasks-1,3),"Access to department operators"],["Rule confirmation",1,1+min(rule_tasks*2,3),"Observed workflow"],["Information and connection preparation",1,2+connections*2,"Confirmed sources, access and owners"],["Platform preparation and end-to-end testing",2,3+min(platform_work,3),"Confirmed rules, usable information paths and completed platform setup"],["User preparation and controlled launch",1,2,"Completed end-to-end testing"]],columns=["Work package","Recommended minimum weeks","Recommended maximum weeks","Must be completed first"])
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
    ["Workflow discovery",3,5+discovery_tasks*2],
    ["Rule confirmation",2,3+rule_tasks*2],
    ["Information and connection preparation",3,5+connections*2],
    ["Configuration and workflow testing",5,8+connections],
    ["User preparation and controlled launch",3,5+int(bool(scope_manual_work))+int(variation!="Same process in first-wave departments")],
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

st.header("4. Risks and lessons")
watch=[]
if variation!="Same process in first-wave departments":watch.append(["Department variation",variation_details.strip() or "The departments may use different rules, approvals or exceptions for the same work.","Compare first-wave departments before copying a configuration.","Before configuration","Likely","Major"])
if labor_work:watch.append(["Union and employment agreement requirements","The covered staff groups or applicable employment requirements have not been fully confirmed.","Confirm the affected workflow rules with Labor Relations before configuration.","While confirming operating rules","Possible","Major"])
if scope_unknown:watch.append(["Unconfirmed current workflow",f"The team cannot yet describe how {solution.lower()} works today.","Observe the selected workflow and confirm the unanswered scope-specific questions.","During workflow discovery","Likely","Major"])
if scope_manual_work:watch.append(["Manual workflow handoffs",f'Manual work remains in: {", ".join(item.lower() for item in scope_manual_work)}.',"Map each handoff and decide whether the first rollout will replace, support or retain it.","During workflow discovery","Possible","Moderate"])
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
watch_df["Outcome"]="Not resolved"
watch_df["Use in future deployments"]="Review after resolution"
watch_df["Suggested playbook change"]=""
if saved_watch:
    for index,item in enumerate(saved_watch[:len(watch_df)]):
        watch_df.at[index,"Outcome"]=item.get("outcome","Not resolved")
        watch_df.at[index,"Use in future deployments"]=item.get("use_in_future_deployments","Review after resolution")
        watch_df.at[index,"Suggested playbook change"]=item.get("suggested_playbook_change","")
watch_df=st.data_editor(watch_df,hide_index=True,width="stretch",num_rows="dynamic",key=f"flags:{choice}:{form_key}",column_config={"Potential issue":st.column_config.TextColumn(width="medium"),"Warning sign":st.column_config.TextColumn(width="large"),"Recommended response":st.column_config.TextColumn(width="large"),"Review point":st.column_config.TextColumn(width="medium"),"Likelihood":st.column_config.SelectboxColumn(options=["Unlikely","Possible","Likely"]),"Impact":st.column_config.SelectboxColumn(options=["Minor","Moderate","Major"]),"Outcome":st.column_config.SelectboxColumn(options=["Not resolved","Resolved as planned","Workaround used","Escalated","Accepted for this rollout"]),"Use in future deployments":st.column_config.SelectboxColumn(options=["Review after resolution","Hospital-specific only","Already covered by the playbook","Reusable lesson","Product or engineering review"]),"Suggested playbook change":st.column_config.TextColumn(width="large")})
likelihood_score={"Unlikely":1,"Possible":2,"Likely":3};impact_score={"Minor":1,"Moderate":2,"Major":3}
watch_df["Score"]=watch_df["Likelihood"].map(likelihood_score).fillna(2)*watch_df["Impact"].map(impact_score).fillna(2)
watch_df["Priority"]=watch_df["Score"].apply(lambda value:"High" if value>=6 else "Medium" if value>=3 else "Low")
priority_view=watch_df.sort_values(["Score","Potential issue"],ascending=[False,True])[["Priority","Potential issue","Likelihood","Impact","Recommended response"]]
st.markdown("**Priority order**")
def color_priority(value):
    return {"High":"background-color:#f6dddd;color:#7b2424;font-weight:700","Medium":"background-color:#fff0c9;color:#765100;font-weight:700","Low":"background-color:#dcefe5;color:#155b39;font-weight:700"}.get(value,"")
st.dataframe(priority_view.style.map(color_priority,subset=["Priority"]),hide_index=True,width="stretch")
st.header("5. Case summary and exports")
st.subheader(case_name)
states=required.Status.tolist()
if "Must wait" in states:readiness="Waiting on a required system"
elif any(s in states for s in ["Temporary route available","Connection required","Needs confirmation"]) or rules!="Documented and confirmed" or owner!="Named" or scope_unknown or labor_work:readiness="Hospital preparation required before end-to-end testing"
elif not platform_open.empty:readiness="Platform preparation required before end-to-end testing"
else:readiness="Ready for end-to-end testing"
if "Temporary route available" in states:decision_needed="Approve a temporary information transfer for the first department or wait for the permanent source."
elif "Needs confirmation" in states:decision_needed="Confirm the unresolved information source and transfer method before approving the launch plan."
elif "Connection required" in states:decision_needed="Confirm who will prepare the required connection and agree its planning time."
elif owner!="Named":decision_needed="Name the hospital decision-maker for the first scope."
elif rules!="Documented and confirmed":decision_needed="Confirm the first department's operating rules before setup."
elif scope_unknown:decision_needed=f"Confirm how {solution.lower()} works today before finalising the setup."
elif labor_work:decision_needed="Confirm the affected staff groups and employment requirements with Labor Relations."
elif not platform_open.empty:decision_needed=f'Complete and check the remaining platform preparation, starting with {platform_open.iloc[0]["Item"].lower()}.'
else:decision_needed="Proceed with first-department setup and complete workflow testing."
critical_package=timing.loc[timing["Recommended maximum weeks"].astype(float).idxmax(),"Work package"]
st.markdown(f"**Recommended first move**  \n{recommended_next_move}")
st.markdown(f"**Why this route**  \n{reason}")
st.markdown(f"**Current readiness**  \n{readiness}")
st.markdown(f"**Estimated timeline**  \n{total[0]:g}–{total[1]:g} weeks to first-department launch. The longest planned work package is {critical_package.lower()}.")
st.markdown("**Immediate priorities**")
for _,item in plan_df.head(3).iterrows():st.write(f'{int(item["Item"])}. {item["Action"]}')
st.warning(f"**Decision required:** {decision_needed}")
st.markdown("**Before expanding**  \nConfirm that the department is using the workflow as intended, resolve important incidents and compare the agreed result with the pre-launch baseline.")

safe_department=re.sub(r"[^a-z0-9]+","_",department.lower()).strip("_") or "department"
assessment={"case_name":case_name,"selection":choice,"scope":{"solution":solution,"capabilities":capabilities,"department":department,"staff_groups":staff,"hospitals":sites},"hospital_context":{"type":profile,"current_owner":governance,"process_variation":variation,"process_variation_details":variation_details,"manual_work":manual,"exceptions":exceptions,"scope_method":scope_method,"scope_decision":scope_decision,"scope_manual":scope_manual,"rules":rules,"labor_rules":labor,"labor_groups":labor_groups,"labor_requirements":labor_requirements,"labor_confirmation":labor_confirmation,"decision_owner":owner,"approvers":approvers},"recommended_rollout":{"route":route,"reason":reason,"readiness":readiness,"decision_required":decision_needed,"main_dependency":critical_text,"estimated_timeline_weeks":{"minimum":total[0],"maximum":total[1]}},"internal_playbook":{"reference":playbook_reference,"url":playbook_url,"connection_status":"Connected" if playbook_url.startswith(("https://","http://")) else "Not connected"},"information_dependencies":df.to_dict("records"),"platform_preparation":platform_df.to_dict("records"),"action_plan":plan_df.to_dict("records"),"timeline":timing.to_dict("records"),"effort_estimate":effort.to_dict("records"),"expansion_estimate":{"departments":next_departments,"hospitals":next_hospitals,"reuse":reuse,"minimum_weeks":wave_min,"maximum_weeks":wave_max},"potential_issues":[{"potential_issue":r["Potential issue"],"warning_sign":r["Warning sign"],"recommended_response":r["Recommended response"],"review_point":r["Review point"],"likelihood":r["Likelihood"],"impact":r["Impact"],"priority":r["Priority"],"outcome":r["Outcome"],"use_in_future_deployments":r["Use in future deployments"],"suggested_playbook_change":r["Suggested playbook change"]} for _,r in watch_df.iterrows()]}
st.subheader("Working files")
e1,e2=st.columns(2)
e1.download_button("Download case action tracker",plan_df.to_csv(index=False),f"hospital_deployment_action_tracker_{safe_department}.csv","text/csv",use_container_width=True)
e2.download_button("Download complete case record",json.dumps(assessment,indent=2,default=str),f"hospital_deployment_case_{safe_department}.json","application/json",use_container_width=True)
with st.expander("Future project-management connection"):
    tool=st.selectbox("Where does the team manage deployment work?",["Not selected","Jira","Asana","Linear","Other"],key=f"project_tool:{form_key}")
    st.write("A future connection would map the case actions, owners, priorities, dates and evidence to the selected system. No live connection is active in this prototype.")
    st.button(f"Send to {tool}" if tool!="Not selected" else "Send to project-management system",disabled=True)
with st.expander("Method and limitations"):
    st.write("Hospital characteristics generate planning assumptions to test, not confirmed problems. Public cases inform common patterns but do not establish a vendor's internal process or exact deployment duration.")
