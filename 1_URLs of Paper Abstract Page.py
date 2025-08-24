import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import os

def create_directories():
    """Create necessary directories for results and backups"""
    os.makedirs('results', exist_ok=True)
    os.makedirs('backup/1_URL_of_paper_abstractions', exist_ok=True)
    os.makedirs('backup/Failed', exist_ok=True)

def load_existing_data():
    """Load existing data from CSV file to check for duplicates"""
    csv_path = 'results/1_URL_of_paper_abstractions.csv'
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
        return existing_df
    return pd.DataFrame()

def generate_date_pairs(start_date, end_date):
    """Generate date pairs for the given range"""
    return [[start_date + timedelta(days=i), start_date + timedelta(days=i + 1)]
            for i in range((end_date - start_date).days)]

def parse_paper_data(paper_element):
    """Extract detailed paper information from HTML element"""
    paper_data = {}
    
    # Extract arXiv URL
    url_element = paper_element.find('p', class_='list-title')
    if url_element:
        url_link = url_element.find('a', href=re.compile(r'https://arxiv\.org/abs'))
        abs_url = url_link.get('href') if url_link else ''
        paper_data['abs_url'] = abs_url
        # Generate HTML URL by replacing /abs/ with /html/
        paper_data['html_url'] = abs_url.replace('/abs/', '/html/') if abs_url else ''
    else:
        paper_data['abs_url'] = ''
        paper_data['html_url'] = ''
    
    # Extract title
    title_element = paper_element.find('p', class_='title')
    paper_data['Title'] = title_element.get_text(strip=True) if title_element else ''
    
    # Extract authors
    authors_element = paper_element.find('p', class_='authors')
    if authors_element:
        author_links = authors_element.find_all('a')
        authors = [link.get_text(strip=True) for link in author_links]
        paper_data['Authors'] = '; '.join(authors)
    else:
        paper_data['Authors'] = ''
    
    # Extract submission and announcement dates
    date_element = paper_element.find('p', class_='is-size-7')
    paper_data['Submitted'] = ''
    paper_data['Originally_announced'] = ''
    
    if date_element:
        date_text = date_element.get_text()
        # Parse submitted date
        submitted_match = re.search(r'Submitted\s+([^;]+)', date_text)
        if submitted_match:
            paper_data['Submitted'] = submitted_match.group(1).strip()
        
        # Parse announced date
        announced_match = re.search(r'originally announced\s+([^.]+)', date_text)
        if announced_match:
            paper_data['Originally_announced'] = announced_match.group(1).strip()
    
    # Extract subjects
    subjects_element = paper_element.find('div', class_='tags')
    if subjects_element:
        subject_tags = subjects_element.find_all('span', class_='tag')
        subjects = [tag.get_text(strip=True) for tag in subject_tags]
        paper_data['Subjects'] = '; '.join(subjects)
    else:
        paper_data['Subjects'] = ''
    
    return paper_data

def check_duplicate_and_update(new_paper, existing_df):
    """Check for duplicates based on Title and update Submitted date if needed"""
    if existing_df.empty:
        return new_paper, False  # No duplicates possible, include paper
    
    # Check if title exists in existing data
    matching_rows = existing_df[existing_df['Title'] == new_paper['Title']]
    
    if matching_rows.empty:
        return new_paper, False  # No duplicate found, include paper
    
    # Title exists - check Submitted date
    existing_submitted = matching_rows.iloc[0]['Submitted']
    new_submitted = new_paper['Submitted']
    
    if existing_submitted == new_submitted:
        return None, True  # Exact duplicate, skip
    else:
        # Different submitted date - need to update existing record
        return new_paper, 'update'

def fetch_arxiv_data(subject, start_date, end_date):
    """Fetch detailed arXiv paper data for given subject and date range"""
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    url = f"https://arxiv.org/search/advanced?advanced=&terms-0-term={subject}&terms-0-operator=AND&terms-0-field=all&classification-physics_archives=all&classification-include_cross_list=include&date-filter_by=date_range&date-year=&date-from_date={start_str}&date-to_date={end_str}&date-date_type=submitted_date&abstracts=hide&size=200&order=-announced_date_first&start=0"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all paper entries
        paper_elements = soup.find_all('li', class_='arxiv-result')
        
        if not paper_elements:
            print(f"No papers found for {subject} from {start_str} to {end_str}")
            return []
        
        papers_data = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for paper_element in paper_elements:
            paper_data = parse_paper_data(paper_element)
            paper_data['Collected_date'] = current_time
            papers_data.append(paper_data)
        
        return papers_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed for {subject} from {start_str} to {end_str}: {str(e)}")
        return None  # Return None to indicate failure

def save_results(papers_data, papers_to_update, existing_df, backup_filename=None):
    """Save results to CSV with duplicate handling and updates"""
    if not papers_data and not papers_to_update:
        print("No new data to save")
        return
    
    csv_path = 'results/1_URL_of_paper_abstractions.csv'
    
    # Handle updates to existing records
    if papers_to_update and not existing_df.empty:
        for paper in papers_to_update:
            # Find the row to update
            mask = existing_df['Title'] == paper['Title']
            if mask.any():
                existing_df.loc[mask, 'Submitted'] = paper['Submitted']
                existing_df.loc[mask, 'Collected_date'] = paper['Collected_date']
                print(f"Updated paper: {paper['Title'][:50]}...")
    
    # Add new papers
    if papers_data:
        new_df = pd.DataFrame(papers_data)
        
        # Reorder columns to match the required format
        column_order = ['Collected_date', 'abs_url', 'html_url', 'Title', 'Authors', 
                       'Submitted', 'Originally_announced', 'Subjects']
        new_df = new_df[column_order]
        
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
    else:
        combined_df = existing_df
    
    # Reset ID column
    combined_df.reset_index(drop=True, inplace=True)
    combined_df.insert(0, 'ID', range(len(combined_df)))
    
    combined_df.to_csv(csv_path, index=False)
    
    # Save backup of new data only
    if backup_filename and papers_data:
        backup_df = pd.DataFrame(papers_data)
        backup_df = backup_df[column_order]
        backup_df.insert(0, 'ID', range(len(backup_df)))
        # Create timestamped backup filename
        timestamp = datetime.now().strftime('%Y-%m-%d %H')
        backup_path = f'backup/1_URL_of_paper_abstractions/1_URL_of_paper_abstractions_{timestamp}.csv'
        backup_df.to_csv(backup_path, index=False)
        print(f"Backup saved: {backup_path}")
    
    print(f"Total papers in database: {len(combined_df)}")
    print(f"New papers added: {len(papers_data) if papers_data else 0}")
    print(f"Papers updated: {len(papers_to_update) if papers_to_update else 0}")

def save_failed_requests(failed_requests, backup_filename=None):
    """Save failed request information to CSV files"""
    if not failed_requests:
        return  # No failed requests to save
    
    failed_df = pd.DataFrame(failed_requests)
    
    # Save main failed list
    failed_csv_path = 'results/Failed_list.csv'
    
    if os.path.exists(failed_csv_path):
        existing_failed_df = pd.read_csv(failed_csv_path)
        combined_failed_df = pd.concat([existing_failed_df, failed_df], ignore_index=True)
    else:
        combined_failed_df = failed_df
    
    combined_failed_df.to_csv(failed_csv_path, index=False)
    print(f"Failed requests saved to: {failed_csv_path}")
    
    # Save backup if provided
    if backup_filename:
        # Create timestamped failed requests backup
        timestamp = datetime.now().strftime('%Y-%m-%d %H')
        backup_path = f'backup/Failed/Failed_list_{timestamp}.csv'
        failed_df.to_csv(backup_path, index=False)
        print(f"Failed requests backup saved to: {backup_path}")

def main():
    create_directories()
    existing_df = load_existing_data()
    
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 8, 3)
    subjects = ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV']
    
    all_papers_data = []
    papers_to_update = []
    failed_requests = []
    request_count = 0
    
    date_pairs = generate_date_pairs(start_date, end_date)
    
    for subject in subjects:
        print(f"======================================================== {subject} ========================================================")
        
        for start_dt, end_dt in date_pairs:
            if request_count % 20 == 0 and request_count > 0:
                print(f"Processed papers so far: {len(all_papers_data) + len(papers_to_update)}")
                time.sleep(10)
            
            print(f" = = = = = = = = = = =   {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
            
            papers_data = fetch_arxiv_data(subject, start_dt, end_dt)
            
            # Check if request failed
            if papers_data is None:
                failed_requests.append({
                    'Subject': subject,
                    'Start_date': start_dt.strftime('%Y-%m-%d'),
                    'End_date': end_dt.strftime('%Y-%m-%d'),
                    'Failed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                request_count += 1
                continue  # Skip to next iteration
            
            # Process each paper for duplicates
            for paper in papers_data:
                result, status = check_duplicate_and_update(paper, existing_df)
                
                if result is None:  # Exact duplicate, skip
                    continue
                elif status == 'update':  # Different submitted date, update
                    papers_to_update.append(result)
                    # Also update the existing_df for subsequent checks
                    mask = existing_df['Title'] == result['Title']
                    if mask.any():
                        existing_df.loc[mask, 'Submitted'] = result['Submitted']
                        existing_df.loc[mask, 'Collected_date'] = result['Collected_date']
                else:  # No duplicate, add as new
                    all_papers_data.append(result)
            
            request_count += 1
    
    # Remove duplicates based on URL and sort
    seen_urls = set()
    unique_papers_data = []
    
    for paper in all_papers_data:
        if paper['abs_url'] not in seen_urls:
            unique_papers_data.append(paper)
            seen_urls.add(paper['abs_url'])
    
    # Sort by URL in descending order
    unique_papers_data.sort(key=lambda x: x['abs_url'], reverse=True)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    backup_filename = f'{today_str}_collected_data.csv'
    
    save_results(unique_papers_data, papers_to_update, existing_df, backup_filename)
    
    # Save failed requests if any
    if failed_requests:
        failed_backup_filename = f'Failed_list_{today_str}.csv'
        save_failed_requests(failed_requests, failed_backup_filename)
        print(f"⚠️ {len(failed_requests)} request(s) failed. Check Failed_list.csv for details.")

if __name__ == "__main__":
    main()