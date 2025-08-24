import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import pickle
import xml.dom.minidom
import re

def remove_outer_tags_and_check_rule(html_with_tags):
    """
    HTML에서 외부 div와 span 태그를 제거하고 규칙 위배 여부를 확인합니다.
    
    규칙:
    1. 첫 번째 태그: <div class="ltx_authors">
    2. 두 번째 태그: <span class="ltx_creator ltx_role_author">
    3. 마지막에서 두 번째 태그: </span>
    4. 마지막 태그: </div>
    
    Args:
        html_with_tags (str): HTML 문자열
        
    Returns:
        tuple: (filtered_html, rule_violation_message)
               - filtered_html: 외부 태그가 제거된 HTML
               - rule_violation_message: 규칙 위배시 메시지, 정상시 None
    """
    if html_with_tags in ["NO_HTML", "NO_ltx_authors"]:
        return html_with_tags, None
    
    try:
        lines = html_with_tags.strip().split('\n')
        lines = [line for line in lines if line.strip()]  # 빈 줄 제거
        
        if len(lines) < 4:
            return html_with_tags, "Too few lines to apply rule"
        
        # 규칙 검사
        first_line = lines[0].strip()
        second_line = lines[1].strip()
        second_last_line = lines[-2].strip()
        last_line = lines[-1].strip()
        
        # 하드코딩된 규칙 체크
        expected_first = '<div class="ltx_authors">'
        expected_second = '<span class="ltx_creator ltx_role_author">'
        expected_second_last = '</span>'
        expected_last = '</div>'
        
        rule_violation = []
        
        if first_line != expected_first:
            rule_violation.append(f"First tag mismatch: expected '{expected_first}', got '{first_line}'")
        
        if second_line != expected_second:
            rule_violation.append(f"Second tag mismatch: expected '{expected_second}', got '{second_line}'")
        
        if second_last_line != expected_second_last:
            rule_violation.append(f"Second last tag mismatch: expected '{expected_second_last}', got '{second_last_line}'")
        
        if last_line != expected_last:
            rule_violation.append(f"Last tag mismatch: expected '{expected_last}', got '{last_line}'")
        
        # 규칙 위배가 있으면 메시지 반환
        if rule_violation:
            violation_message = "; ".join(rule_violation)
            return html_with_tags, violation_message
        
        # 규칙이 정상이면 외부 4개 태그 제거
        inner_lines = lines[2:-2]  # 첫 2줄과 마지막 2줄 제거
        
        # 들여쓰기 조정 (4칸씩 줄임)
        adjusted_lines = []
        for line in inner_lines:
            if line.startswith('    '):  # 4칸 이상 들여쓰기된 경우
                adjusted_lines.append(line[4:])  # 4칸 제거
            else:
                adjusted_lines.append(line)
        
        filtered_html = '\n'.join(adjusted_lines)
        return filtered_html, None
        
    except Exception as e:
        return html_with_tags, f"Error processing HTML: {str(e)}"

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
            # HTML 태그 포함하여 hierarchical indentation으로 추출
            try:
                # BeautifulSoup의 prettify()는 기본 2칸 들여쓰기 사용
                pretty_html = ltx_authors_div.prettify()
                # 2칸을 4칸으로 변경
                lines = pretty_html.split('\n')
                formatted_lines = []
                for line in lines:
                    # 앞의 공백 개수 세기
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 0:
                        # 2칸 단위를 4칸 단위로 변경
                        new_indent = ' ' * (leading_spaces * 2)
                        formatted_lines.append(new_indent + line.lstrip())
                    else:
                        formatted_lines.append(line)
                html_with_tags = '\n'.join(formatted_lines)
            except:
                # prettify 실패시 원본 HTML 사용
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

def save_html_raw_text_filtered_pickle(df):
    """html_raw_text_with_tags_filtered 데이터를 pickle 형식으로 저장합니다."""
    try:
        # html_raw_text_with_tags_filtered 컬럼만 추출
        html_raw_text_filtered_data = df['html_raw_text_with_tags_filtered'].tolist()
        
        # pickle 파일로 저장
        pickle_path = "./results/html_raw_text_with_tags_filtered.p"
        with open(pickle_path, 'wb') as f:
            pickle.dump(html_raw_text_filtered_data, f)
        
        print(f"Pickle 파일 저장 완료 (필터링된 태그): {pickle_path}")
        
    except Exception as e:
        print(f"Pickle 저장 중 오류 발생 (필터링된 태그): {str(e)}")

def save_html_raw_text_filtered_txt(df):
    """html_raw_text_with_tags_filtered 데이터를 txt 파일로 저장합니다."""
    try:
        txt_path = "./results/html_raw_text_with_tags_filtered.txt"
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            for idx, text in enumerate(df['html_raw_text_with_tags_filtered']):
                f.write(f"=== Paper {idx + 1} ===\n")
                f.write(str(text))
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"TXT 파일 저장 완료 (필터링된 태그): {txt_path}")
        
    except Exception as e:
        print(f"TXT 저장 중 오류 발생 (필터링된 태그): {str(e)}")

def main():
    """메인 실행 함수"""
    # CSV 파일 읽기
    input_file = "./results/1_URL_of_paper_abstractions.csv"
    output_file = "./results/2_html_raw_text.csv"
    
    try:
        df = pd.read_csv(input_file)[:3]
        print(f"총 {len(df)}개의 논문 데이터를 로드했습니다.")
        
        # 필요한 컬럼들 초기화
        df['html_raw_text'] = ""
        df['html_raw_text_with_tags'] = ""
        df['html_raw_text_with_tags_filtered'] = ""
        df['tag_rule_violation'] = ""
        
        # 각 HTML URL에서 ltx_authors 태그 내용 추출
        for idx, row in df.iterrows():
            html_url = row['html_url']
            
            print(f"처리 중 ({idx+1}/{len(df)}): {html_url}")
            
            # HTML에서 ltx_authors 태그 추출 (텍스트와 HTML 태그 포함 버전)
            text_only, html_with_tags = extract_ltx_authors(html_url)
            df.at[idx, 'html_raw_text'] = text_only
            df.at[idx, 'html_raw_text_with_tags'] = html_with_tags
            
            # 외부 태그 제거 및 규칙 검사
            filtered_html, rule_violation = remove_outer_tags_and_check_rule(html_with_tags)
            df.at[idx, 'html_raw_text_with_tags_filtered'] = filtered_html
            df.at[idx, 'tag_rule_violation'] = rule_violation if rule_violation else ""
            
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
        
        # html_raw_text_with_tags_filtered 데이터를 pickle과 txt로도 저장
        save_html_raw_text_filtered_pickle(df)
        save_html_raw_text_filtered_txt(df)
        
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