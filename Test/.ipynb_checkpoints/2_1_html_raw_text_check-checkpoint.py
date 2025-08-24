import pandas as pd
import pickle

def load_csv_data():
    """CSV 파일에서 html_raw_text 데이터를 불러옵니다."""
    try:
        csv_path = "./results/2_html_raw_text.csv"
        df = pd.read_csv(csv_path)
        
        print(f"=== CSV 파일 로드 결과 ===")
        print(f"파일 경로: {csv_path}")
        print(f"전체 논문 수: {len(df)}")
        print(f"html_raw_text 컬럼 존재: {'html_raw_text' in df.columns}")
        
        if 'html_raw_text' in df.columns:
            # 상태별 개수 확인
            no_html_count = len(df[df['html_raw_text'] == 'NO_HTML'])
            no_ltx_authors_count = len(df[df['html_raw_text'] == 'NO_ltx_authors'])
            success_count = len(df[(df['html_raw_text'] != 'NO_HTML') & 
                                 (df['html_raw_text'] != 'NO_ltx_authors')])
            
            print(f"성공: {success_count}개")
            print(f"NO_HTML: {no_html_count}개")
            print(f"NO_ltx_authors: {no_ltx_authors_count}개")
            
            # 첫 번째 성공적인 데이터 예시 출력
            success_data = df[(df['html_raw_text'] != 'NO_HTML') & 
                            (df['html_raw_text'] != 'NO_ltx_authors')]
            if not success_data.empty:
                first_success = success_data.iloc[0]
                print(f"\n=== 첫 번째 성공 데이터 예시 ===")
                print(f"논문 제목: {first_success['Title']}")
                print(f"HTML Raw Text 길이: {len(str(first_success['html_raw_text']))}")
                print(f"HTML Raw Text 미리보기 (첫 200자):")
                print(repr(str(first_success['html_raw_text'])[:200]))
        
        return df
        
    except FileNotFoundError:
        print(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None
    except Exception as e:
        print(f"CSV 로드 중 오류: {str(e)}")
        return None

def load_pickle_data():
    """Pickle 파일에서 html_raw_text 데이터를 불러옵니다."""
    try:
        pickle_path = "./results/html_raw_text.p"
        
        with open(pickle_path, 'rb') as f:
            html_raw_text_list = pickle.load(f)
        
        print(f"\n=== Pickle 파일 로드 결과 ===")
        print(f"파일 경로: {pickle_path}")
        print(f"전체 데이터 수: {len(html_raw_text_list)}")
        print(f"데이터 타입: {type(html_raw_text_list)}")
        
        # 상태별 개수 확인
        no_html_count = sum(1 for text in html_raw_text_list if text == 'NO_HTML')
        no_ltx_authors_count = sum(1 for text in html_raw_text_list if text == 'NO_ltx_authors')
        success_count = sum(1 for text in html_raw_text_list 
                          if text != 'NO_HTML' and text != 'NO_ltx_authors')
        
        print(f"성공: {success_count}개")
        print(f"NO_HTML: {no_html_count}개")
        print(f"NO_ltx_authors: {no_ltx_authors_count}개")
        
        # 첫 번째 성공적인 데이터 예시 출력
        for i, text in enumerate(html_raw_text_list):
            if text not in ['NO_HTML', 'NO_ltx_authors']:
                print(f"\n=== 첫 번째 성공 데이터 예시 (인덱스 {i}) ===")
                print(f"텍스트 길이: {len(text)}")
                print(f"텍스트 미리보기 (첫 200자):")
                print(repr(text[:200]))
                break
        
        return html_raw_text_list
        
    except FileNotFoundError:
        print(f"Pickle 파일을 찾을 수 없습니다: {pickle_path}")
        return None
    except Exception as e:
        print(f"Pickle 로드 중 오류: {str(e)}")
        return None

def load_txt_data():
    """TXT 파일에서 html_raw_text 데이터를 불러옵니다."""
    try:
        txt_path = "./results/html_raw_text.txt"
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n=== TXT 파일 로드 결과 ===")
        print(f"파일 경로: {txt_path}")
        print(f"전체 파일 크기: {len(content)} 문자")
        
        # 논문 구분자로 분리
        papers = content.split("=" * 50)
        papers = [paper.strip() for paper in papers if paper.strip()]
        
        print(f"분리된 논문 수: {len(papers)}")
        
        # 첫 번째 논문 예시 출력
        if papers:
            print(f"\n=== 첫 번째 논문 데이터 예시 ===")
            first_paper = papers[0]
            print(f"텍스트 길이: {len(first_paper)}")
            print(f"텍스트 미리보기 (첫 300자):")
            print(repr(first_paper[:300]))
        
        return content
        
    except FileNotFoundError:
        print(f"TXT 파일을 찾을 수 없습니다: {txt_path}")
        return None
    except Exception as e:
        print(f"TXT 로드 중 오류: {str(e)}")
        return None

def compare_data_formats():
    """세 가지 형식의 데이터를 비교합니다."""
    print(f"\n{'='*60}")
    print(f"{'데이터 형식 비교 분석':^60}")
    print(f"{'='*60}")
    
    # 각 형식 로드
    csv_df = load_csv_data()
    pickle_data = load_pickle_data()
    txt_data = load_txt_data()
    
    # 데이터 일관성 검증
    print(f"\n=== 데이터 일관성 검증 ===")
    
    if csv_df is not None and pickle_data is not None:
        if 'html_raw_text' in csv_df.columns:
            csv_html_texts = csv_df['html_raw_text'].tolist()
            
            # 길이 비교
            csv_len = len(csv_html_texts)
            pickle_len = len(pickle_data)
            print(f"CSV 데이터 수: {csv_len}")
            print(f"Pickle 데이터 수: {pickle_len}")
            print(f"길이 일치: {csv_len == pickle_len}")
            
            # 내용 비교 (첫 5개)
            if csv_len == pickle_len:
                matches = 0
                for i in range(min(5, csv_len)):
                    if str(csv_html_texts[i]) == str(pickle_data[i]):
                        matches += 1
                
                print(f"첫 5개 데이터 일치 개수: {matches}/5")
                
                # 특수 문자 보존 확인
                for i in range(min(3, csv_len)):
                    csv_text = str(csv_html_texts[i])
                    pickle_text = str(pickle_data[i])
                    
                    csv_newlines = csv_text.count('\\n')
                    pickle_newlines = pickle_text.count('\n')
                    
                    if csv_newlines > 0 or pickle_newlines > 0:
                        print(f"\n논문 {i+1} 특수문자 보존 확인:")
                        print(f"CSV에서 \\n 개수: {csv_newlines}")
                        print(f"Pickle에서 \\n 개수: {pickle_newlines}")
                        print(f"CSV 샘플: {repr(csv_text[:100])}")
                        print(f"Pickle 샘플: {repr(pickle_text[:100])}")
                        break

def main():
    """메인 실행 함수"""
    print("HTML Raw Text 데이터 검증 도구")
    print("=" * 60)
    
    # 각 형식별 데이터 로드 및 비교
    compare_data_formats()
    
    print(f"\n{'='*60}")
    print("검증 완료!")

if __name__ == "__main__":
    main()