from shared.intelligence.contradictions import detect_p4_in_progress

def analyze_operational_health(tasks):
    findings = []

    findings.extend(detect_p4_in_progress(tasks))

    return findings