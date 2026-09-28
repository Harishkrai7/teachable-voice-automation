import uuid
from typing import List, Dict, Any, Optional
from app.models.schemas import Action, Flow, ProcessResponse, TeachRequest, ReplayRequest, Slots
from app.services.storage_service import save_flow, find_matching_flows

SENSITIVE_ACTIONS = ["PAYMENT", "OTP", "PASSWORD", "PIN"]

def check_safety(actions: List[Action]) -> Optional[str]:
    for a in actions:
        if a.action in SENSITIVE_ACTIONS or \
           (a.target and a.target.upper() in SENSITIVE_ACTIONS) or \
           (a.value and a.value.upper() in SENSITIVE_ACTIONS):
            return "SENSITIVE_ACTION"
    return None

def generalize_flow(intent: str, app: str, slots: Slots, concrete_actions: List[Action]) -> ProcessResponse:
    # Check Safety
    safety_issue = check_safety(concrete_actions)
    if safety_issue:
        return ProcessResponse(success=True, type="STOP", reason=safety_issue)

    generalized_steps = []
    slot_dict = slots.model_dump(exclude_none=True)
    
    # Reverse mapping: value -> slot_name
    # Note: we stringify values to match them in actions
    val_to_slot = {str(v).lower(): k for k, v in slot_dict.items()}

    for act in concrete_actions:
        gen_act = Action(action=act.action)
        
        # Substitute target
        if act.target:
            t_lower = act.target.lower()
            found = False
            for val, slot_name in val_to_slot.items():
                if val in t_lower:
                    gen_act.target = f"{{{{{slot_name}}}}}"
                    found = True
                    break
            if not found:
                gen_act.target = act.target
                
        # Substitute value
        if act.value:
            v_lower = str(act.value).lower()
            found = False
            for val, slot_name in val_to_slot.items():
                if val in v_lower:
                    gen_act.value = f"{{{{{slot_name}}}}}"
                    found = True
                    break
            if not found:
                gen_act.value = act.value
                
        generalized_steps.append(gen_act)
        
    flow = Flow(
        flowId=str(uuid.uuid4())[:8],
        intent=intent,
        app=app,
        slots=slot_dict,
        steps=generalized_steps,
        stopBefore=SENSITIVE_ACTIONS
    )
    
    save_flow(flow)
    
    return ProcessResponse(
        success=True,
        mode="TEACH",
        flow=flow
    )

def replay_flow(intent: str, app: str, slots: Slots) -> ProcessResponse:
    matches = find_matching_flows(intent, app)
    
    if len(matches) == 0:
        return ProcessResponse(success=True, type="NOT_LEARNED", message="I have not learned a flow for this task yet.")
        
    if len(matches) > 1:
        return ProcessResponse(success=True, type="ASK_USER", question="I know multiple ways to do this. Which one do you mean?")
        
    flow = matches[0]
    
    # Safety Check on the learned flow steps just in case
    safety_issue = check_safety(flow.steps)
    if safety_issue:
        return ProcessResponse(success=True, type="STOP", reason=safety_issue)
        
    # Parameter substitution
    slot_dict = slots.model_dump()
    final_actions = []
    
    for step in flow.steps:
        new_act = Action(action=step.action)
        
        # Check target
        if step.target and step.target.startswith("{{") and step.target.endswith("}}"):
            slot_name = step.target[2:-2]
            val = slot_dict.get(slot_name)
            if val is None:
                return ProcessResponse(success=True, type="ASK_USER", question=f"What {slot_name} would you like?")
            new_act.target = str(val)
        else:
            new_act.target = step.target
            
        # Check value
        if step.value and step.value.startswith("{{") and step.value.endswith("}}"):
            slot_name = step.value[2:-2]
            val = slot_dict.get(slot_name)
            if val is None:
                return ProcessResponse(success=True, type="ASK_USER", question=f"What {slot_name} would you like?")
            new_act.value = str(val)
        else:
            new_act.value = step.value
            
        final_actions.append(new_act)
        
    return ProcessResponse(
        success=True,
        mode="REPLAY",
        flowId=flow.flowId,
        intent=intent,
        slots=slot_dict,
        actions=final_actions
    )
