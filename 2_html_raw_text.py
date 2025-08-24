import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import pickle

def extract_ltx_authors(html_url):
    """
    주어진 HTML URL에서 <div class="ltx_authors"> 태그의 텍스트와 HTML을 추출합니다.
    
    Args:
        html_url (str): 추출할 HTML 페이지의 URL
        
    Returns:
        tuple: (text_only, html_with_tags) - 텍스트만, HTML 태그 포함 버전
               접근 불가능한 경우 ("NO_HTML", "NO_HTML")
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(html_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # HTML이 없다는 메시지 체크
        if ("No HTML for" in response.text or 
            "HTML is not available for the source" in response.text):
            return ("NO_HTML", "NO_HTML")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ltx_authors 태그 찾기
        ltx_authors_div = soup.find('div', class_='ltx_authors')
        
        if ltx_authors_div:
            # 텍스트만 추출
            text_only = ltx_authors_div.get_text()
            # HTML 태그 포함하여 추출
            html_with_tags = str(ltx_authors_div)
            return (text_only, html_with_tags)
        else:
            return ("NO_ltx_authors", "NO_ltx_authors")
            
    except Exception as e:
        print(f"Error processing {html_url}: {str(e)}")
        return ("NO_HTML", "NO_HTML")

def create_backup_directory():
    """백업 디렉토리를 생성합니다."""
    backup_dir = "./backup/2_html_raw_text"
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def save_backup_file(df, backup_dir):
    """백업 파일을 저장합니다."""
    current_time = datetime.now().strftime("%Y-%m-%d %H")
    backup_filename = f"2_html_raw_text_{current_time}.csv"
    backup_path = os.path.join(backup_dir, backup_filename)
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"백업 파일 저장 완료: {backup_path}")

def save_html_raw_text_pickle(df):
    """html_raw_text 데이터를 pickle 형식으로 저장합니다."""
    try:
        # html_raw_text 컬럼만 추출
        html_raw_text_data = df['html_raw_text'].tolist()
        
        # pickle 파일로 저장
        pickle_path = "./results/html_raw_text.p"
        with open(pickle_path, 'wb') as f:
            pickle.dump(html_raw_text_data, f)
        
        print(f"Pickle 파일 저장 완료: {pickle_path}")
        
    except Exception as e:
        print(f"Pickle 저장 중 오류 발생: {str(e)}")

def save_html_raw_text_txt(df):
    """html_raw_text 데이터를 txt 파일로 저장합니다."""
    try:
        txt_path = "./results/html_raw_text.txt"
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            for idx, text in enumerate(df['html_raw_text']):
                f.write(f"=== Paper {idx + 1} ===\n")
                f.write(str(text))
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"TXT 파일 저장 완료: {txt_path}")
        
    except Exception as e:
        print(f"TXT 저장 중 오류 발생: {str(e)}")

def save_html_raw_text_with_tags_pickle(df):
    """html_raw_text_with_tags 데이터를 pickle 형식으로 저장합니다."""
    try:
        # html_raw_text_with_tags 컬럼만 추출
        html_raw_text_with_tags_data = df['html_raw_text_with_tags'].tolist()
        
        # pickle 파일로 저장
        pickle_path = "./results/html_raw_text_with_tags.p"
        with open(pickle_path, 'wb') as f:
            pickle.dump(html_raw_text_with_tags_data, f)
        
        print(f"Pickle 파일 저장 완료 (태그 포함): {pickle_path}")
        
    except Exception as e:
        print(f"Pickle 저장 중 오류 발생 (태그 포함): {str(e)}")

def save_html_raw_text_with_tags_txt(df):
    """html_raw_text_with_tags 데이터를 txt 파일로 저장합니다."""
    try:
        txt_path = "./results/html_raw_text_with_tags.txt"
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            for idx, text in enumerate(df['html_raw_text_with_tags']):
                f.write(f"=== Paper {idx + 1} ===\n")
                f.write(str(text))
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"TXT 파일 저장 완료 (태그 포함): {txt_path}")
        
    except Exception as e:
        print(f"TXT 저장 중 오류 발생 (태그 포함): {str(e)}")

def main():
    """메인 실행 함수"""
    # CSV 파일 읽기
    input_file = "./results/1_URL_of_paper_abstractions.csv"
    output_file = "./results/2_html_raw_text.csv"
    
    try:
        df = pd.read_csv(input_file)[:3]
        print(f"총 {len(df)}개의 논문 데이터를 로드했습니다.")
        
        # html_raw_text 및 html_raw_text_with_tags 컬럼 초기화
        df['html_raw_text'] = ""
        df['html_raw_text_with_tags'] = ""
        
        # 각 HTML URL에서 ltx_authors 태그 내용 추출
        for idx, row in df.iterrows():
            html_url = row['html_url']
            
            print(f"처리 중 ({idx+1}/{len(df)}): {html_url}")
            
            # HTML에서 ltx_authors 태그 추출 (텍스트와 HTML 태그 포함 버전)
            text_only, html_with_tags = extract_ltx_authors(html_url)
            df.at[idx, 'html_raw_text'] = text_only
            df.at[idx, 'html_raw_text_with_tags'] = html_with_tags
            
            # 20개마다 10초 대기 (서버 부하 방지)
            if (idx + 1) % 20 == 0:
                print(f"{idx + 1}개 처리 완료. 10초 대기...")
                time.sleep(10)
            else:
                # 각 요청 간 1초 대기
                time.sleep(1)
        
        # 백업 디렉토리 생성 및 백업 파일 저장
        backup_dir = create_backup_directory()
        save_backup_file(df, backup_dir)
        
        # 메인 결과 파일 저장
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"메인 결과 파일 저장 완료: {output_file}")
        
        # html_raw_text 데이터를 pickle과 txt로도 저장
        save_html_raw_text_pickle(df)
        save_html_raw_text_txt(df)
        
        # html_raw_text_with_tags 데이터를 pickle과 txt로도 저장
        save_html_raw_text_with_tags_pickle(df)
        save_html_raw_text_with_tags_txt(df)
        
        # 결과 통계
        no_html_count = len(df[df['html_raw_text'] == 'NO_HTML'])
        no_ltx_authors_count = len(df[df['html_raw_text'] == 'NO_ltx_authors'])
        success_count = len(df[(df['html_raw_text'] != 'NO_HTML') & (df['html_raw_text'] != 'NO_ltx_authors')])
        
        print(f"\n=== 처리 결과 ===")
        print(f"성공적으로 추출된 논문: {success_count}개")
        print(f"HTML 접근 불가능한 논문: {no_html_count}개")
        print(f"ltx_authors 태그가 없는 논문: {no_ltx_authors_count}개")
        print(f"전체 논문 수: {len(df)}개")
        
    except FileNotFoundError:
        print(f"입력 파일을 찾을 수 없습니다: {input_file}")
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()