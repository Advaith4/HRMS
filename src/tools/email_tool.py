"""
src/tools/email_tool.py
Email Drafting Tool with Human-in-the-Loop Governance for TalentForge AI.
Generates candidate communication drafts requiring explicit HR review and authorization before dispatch.
"""
import uuid
from typing import Literal, Type
from pydantic import BaseModel, Field

from src.tools.base_tool import BaseHRMSTool


class EmailDraftInput(BaseModel):
    candidate_id: int = Field(description="Target candidate identifier")
    candidate_name: str = Field(description="Full name of the candidate")
    candidate_email: str = Field(description="Destination email address")
    job_title: str = Field(description="Associated job title")
    email_type: Literal["interview_invitation", "rejection_polite", "offer_letter", "assessment_reminder"] = Field(
        description="Type of candidate communication"
    )
    interview_link: str | None = Field(default=None, description="Optional interview session or meeting URL")
    company_name: str = Field(default="TalentForge AI", description="Employer company name")


class EmailDraftOutput(BaseModel):
    draft_id: str = Field(description="Unique draft identifier")
    recipient_email: str = Field(description="Destination email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Formatted email body text")
    status: str = Field(default="draft", description="Current message status ('draft' | 'approved' | 'dispatched')")
    requires_hr_approval: bool = Field(default=True, description="Safety flag enforcing human confirmation")


class EmailDraftTool(BaseHRMSTool):
    name: str = "EmailDraftTool"
    description: str = "Generates personalized candidate communication drafts requiring HR authorization before sending."
    args_schema: Type[BaseModel] = EmailDraftInput
    return_schema: Type[BaseModel] = EmailDraftOutput

    def _run(
        self,
        candidate_id: int,
        candidate_name: str,
        candidate_email: str,
        job_title: str,
        email_type: Literal["interview_invitation", "rejection_polite", "offer_letter", "assessment_reminder"],
        interview_link: str | None = None,
        company_name: str = "TalentForge AI",
    ) -> EmailDraftOutput:
        draft_id = f"draft-{uuid.uuid4().hex[:8]}"

        if email_type == "interview_invitation":
            subject = f"Interview Invitation: {job_title} at {company_name}"
            link_str = f"\n\nPlease join your AI screening room using this link: {interview_link}" if interview_link else ""
            body = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for applying for the {job_title} position at {company_name}. "
                f"We were impressed by your background and would love to invite you to the next stage of our interview process.{link_str}\n\n"
                f"Best regards,\nTalent Acquisition Team\n{company_name}"
            )

        elif email_type == "rejection_polite":
            subject = f"Update regarding your application for {job_title}"
            body = (
                f"Dear {candidate_name},\n\n"
                f"Thank you for taking the time to apply for the {job_title} role at {company_name}. "
                f"After careful consideration, we have decided to move forward with other candidates whose experience more closely aligns with our current needs.\n\n"
                f"We appreciate your interest in {company_name} and wish you all the best in your job search.\n\n"
                f"Sincerely,\nTalent Acquisition Team\n{company_name}"
            )

        elif email_type == "offer_letter":
            subject = f"Job Offer: {job_title} with {company_name}!"
            body = (
                f"Dear {candidate_name},\n\n"
                f"On behalf of {company_name}, I am thrilled to offer you the position of {job_title}! "
                f"We were thoroughly impressed by your skills and look forward to welcoming you to the team.\n\n"
                f"Your formal offer details and onboarding documents will follow shortly.\n\n"
                f"Warm regards,\nPeople Operations\n{company_name}"
            )

        else:  # assessment_reminder
            subject = f"Reminder: Next Steps for your {job_title} Application"
            body = (
                f"Dear {candidate_name},\n\n"
                f"This is a gentle reminder regarding your application for the {job_title} position at {company_name}. "
                f"Please ensure your profile and skills assessment are completed at your earliest convenience.\n\n"
                f"Best regards,\nTalent Acquisition Team\n{company_name}"
            )

        return EmailDraftOutput(
            draft_id=draft_id,
            recipient_email=candidate_email,
            subject=subject,
            body=body,
            status="draft",
            requires_hr_approval=True,
        )


email_draft_tool = EmailDraftTool()

