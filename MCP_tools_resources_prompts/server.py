# MCP_tools_resources_prompts/server.py

import json
import requests
from typing import List, Dict, Optional
from PyPDF2 import PdfReader
from fastmcp import FastMCP
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(".")
JOBS_DIR = BASE_DIR / "jobs" / "saved_by_candidate"
TEMP_DIR = BASE_DIR / "jobs" / "temp"
RESUME_PATH = BASE_DIR / "resume" / "resume.pdf"

JOBS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

PARENT_DIR = BASE_DIR.parent
load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

mcp = FastMCP("Job Market Explorer")

@mcp.tool
def search_jobs(role:str, location:str, max_results:int=5) -> List[Dict]:
    """
    Fetch jobs using Jsearch API and store them temporarily. Return key info.

    Args:
        role: The role to search for
        location: The location to search for
        max_results: The max number of jobs to return
    
        Returns:
            A list of dictionaries containing the job information
    """
    headers ={
        "X-RapidAPI-Key":RAPIDAPI_KEY,
        "X-RapidAPI-Host":RAPIDAPI_HOST
    }
    query =f"{role} in {location}"
    url = f"https://{RAPIDAPI_HOST}/search?query={query}&num_pages=1"

    response = requests.get(url, headers=headers)
    data = response.json()
    job_list = data.get("data",[])[:max_results]

    if not job_list:
        return [{"message":"No jobs found"}]
    
    temp_path = TEMP_DIR / "fetched_jobs_temp.json"
    with open(temp_path,"w") as f:
        json.dump(job_list,f, indent=2)
    
    results = []
    for job in job_list:
        desc = job.get("job_description","")
        if isinstance(desc,str):
            if len(desc)<=1000:
                summary = desc
            else:
                summary = desc[:1000] + ("\n...\n" if len(desc)>2000 else "") + desc[-1000:]
        else:
            summary=""

        results.append({
            "job_id":job.get("job_id"),
            "title":job.get("job_title"),
            "company":job.get("employer_name"),
            "location":job.get("job_city"),
            "description":summary,
            "apply_link":job.get("job_apply_link","Not provided")
        })
    return results

@mcp.tool
def save_job(job_id:str, salary : Optional[str]=None) -> str:
    """
    Save a specific job from temporary list into candidate's saved folder.
    If the salary is not provided, it tries to extract it from the fetched job data
    
    Args:
        job_id: The ID of the job to save.
        salary (optional) : The salary of the job to save.
    
    Returns:
        A string indicating the job was saved successfully
    """
    temp_path = TEMP_DIR / "fetched_jobs_temp.json"

    if not temp_path.exists():
        return "No fetched jobs available. Please run search_jobs first"
    
    with open(temp_path,"r") as f:
        jobs = json.load(f)
    
    selected = next((job for job in jobs if job.get("job_id") == job_id),None)
    if not selected:
        return f"Job ID {job_id} not found in fetched data"
    final_salary = salary

    if not final_salary:
        currency = selected.get("salary_currency")
        min_base = selected.get("min_base_salary") or selected.get("job_min_salary")
        max_base = selected.get("max_base_salary") or selected.get("job_max_salary")
        min_add = selected.get("min_additional_pay")
        max_add = selected.get("max_additional_pay")
        salary_period = selected.get("job_salary_period")

        if currency and min_base and max_base:
            total_min = int(min_base + (min_add or 0))
            total_max = int(max_base + (max_add or 0))
            per = f"{salary_period.lower()}" if salary_period else ""
            final_salary = f"{currency} {total_min:,} - {total_max:,} {per}"
    
    if not final_salary:
        final_salary = "Not specified"
    
    job_data ={
        "title":selected.get("job_title","Not specified"),
        "company":selected.get("employer_name","Not specified"),
        "location":selected.get("job_city","Not specified"),
        "description":selected.get("job_description","Not specified"),
        "employment_type":selected.get("job_employment_type","Not specified"),
        "posted_at":selected.get("job_posted_at_datetime_utc","Not specified"),
        "apply_link":selected.get("job_apply_link","Not specified"),
        "salary":final_salary,
    }

    role_folder = JOBS_DIR / "general"
    role_folder.mkdir(exist_ok=True)
    job_file = role_folder / f"{job_id}.json"
    with open(job_file,"w") as f:
        json.dump(job_data,f,indent=2)
    
    return f"Job {job_id} saved successfully with salary: {final_salary}"


@mcp.resource("resume://default")
def candidate_resume() -> str:
    """
    Extract text from resume.pdf and return as markdown
    """
    try:
        reader = PdfReader(str(RESUME_PATH))
        text = "\n\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        return f" Resume Content\n\n{text.strip() or 'No reable content.'}"
    except Exception as e:
        return f"Error reading resume: {e}"
    
@mcp.resource("jobs://saved")
def get_saved_jobs()->str:
    """
    Return markdown listing of all saved jobs
    """
    content = "# Saved Jobs\n\n"
    for file in JOBS_DIR.glob("**/*.json"):
        try:
            with open(file,"r") as f:
                job = json.load(f)

                content += f"## {job.get('title','Untitled')}\n"
                content += f"- **Company**: {job.get('company')}\n"
                content += f"- **Location**: {job.get('location')}\n"
                content += f"- **Description**: {job.get('description')}\n"
                content += f"- **Employment Type**: {job.get('employment_type')}\n"
                content += f"- **Apply**: [Link]({job.get('apply_link')})\n"
                content += f"- **Salary**: [Link]({job.get('salary')})\n"
        except Exception:
            continue
    
    if content.strip() == "# Saved Jobs":
        return "# No saved jobs found"
    return content

@mcp.prompt()
def analyze_job_market(role:str, location:str, num_jobs:int = 5) -> str:
    """
    Analyze the job market for top {num_jobs} for '{role}' in '{location}'
    """
    return f"""Analyze the job market for top {num_jobs} jobs for '{role}' in '{location}'.

            Steps:
            1. Run job search mcp tool with suitable roles and locations.
            2. Review fields like title, company, type, and description.
            3. Summarize:
            - Most common roles
            - Repeated skills or keywords
            - Salary trends (if any)
            - Remote vs onsite distribution

            Structure insights clearly in markdown format."""
                

@mcp.prompt()
def personalized_job_recommender()->str:
    """
    Use the resume to extract key skills, interests, amd preferred job types.
    """
    return """Use the resume to extract key skills, interests, and preferred job types.
            Then:
            1. Call job search mcp tool with suitable roles and locations.
            2. Review descriptions and recommend jobs.
            3. Optionally call save job mcp tool on top matches.

            Output sections:
            - Top Matches
            - Stretch Roles
            - Company Highlights
            """

@mcp.prompt()
def create_match_report()->str:
    """
    Given the attached jobs data and resume, create a concise and accurate summary of how well the resume matches the jobs.
    """
    return """Given the attached jobs data and resume, create a concise and accurate summary of how well the resume matches the jobs.

    Output sections:
    - Job Summary
    - Resume Summary
    - Job Match Summary
    """

if __name__ =="__main__":
    mcp.run(transport="stdio")

