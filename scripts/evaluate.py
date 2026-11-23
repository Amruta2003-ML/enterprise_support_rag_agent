import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.agent import run_agent
from app.schemas import ChatRequest

eval_cases = [
    {
        "question": "VPN is connected but internal GitLab is unreachable. What should I check?",
        "department": "engineering",
        "expected_keywords": ["vpn", "gitlab"],
    },
    {
        "question": "What should I do if internal DNS does not resolve after VPN connects?",
        "department": "all",
        "expected_keywords": ["dns", "vpn"],
    },
    {
        "question": "How do I troubleshoot Okta Verify MFA push notifications on my phone?",
        "department": "all",
        "expected_keywords": ["okta", "mfa"],
    },
    {
        "question": "My laptop prompted for a 48-digit BitLocker recovery key on boot. How do I get it?",
        "department": "finance",
        "expected_keywords": ["bitlocker", "recovery"],
    },
    {
        "question": "How do I request a commercial Docker Desktop license?",
        "department": "engineering",
        "expected_keywords": ["docker", "license"],
    },
]


def run_evaluation():
    print("=" * 60)
    print("Enterprise IT Support Agent - Automated Evaluation Suite")
    print("=" * 60)

    passed = 0
    total = len(eval_cases)

    for i, case in enumerate(eval_cases, 1):
        q = case["question"]
        dept = case["department"]
        expected = case["expected_keywords"]

        print(f"\n[Case {i}/{total}] Dept: {dept}")
        print(f"Question: {q}")

        req = ChatRequest(
            user_id="eval_runner",
            department=dept,
            message=q,
            conversation_id=f"eval_case_{i}",
        )
        response = run_agent(req)
        answer = response.answer.lower()

        matches = [kw for kw in expected if kw.lower() in answer]
        ok = len(matches) == len(expected)
        if ok:
            passed += 1

        status_str = "PASSED" if ok else "FAILED"
        print(f"Status: {status_str} ({len(matches)}/{len(expected)} keywords found)")
        print(f"Tools Used: {response.tools_used}")
        print(f"Citations: {[c.source for c in response.citations]}")
        print(f"Answer snippet: {response.answer[:140]}...")

    print("\n" + "=" * 60)
    print(f"Evaluation Finished: {passed}/{total} Passed (Pass Rate: {passed/total * 100:.1f}%)")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
