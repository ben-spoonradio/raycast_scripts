import pandas as pd
import json
import os

def json_to_excel(json_file='questions.json', excel_file='questions.xlsx'):
    """JSON 파일을 엑셀 형식으로 변환하여 저장"""
    try:
        # JSON 파일 읽기
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = data['raycast_questions']
        
        # DataFrame 생성
        df = pd.DataFrame(questions)
        
        # 엑셀 파일로 저장
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"✅ JSON 데이터가 {excel_file}로 저장되었습니다.")
        
    except FileNotFoundError:
        print(f"❌ {json_file} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def excel_to_json(excel_file='questions.xlsx', json_file='questions_from_excel.json'):
    """엑셀 파일을 JSON 형식으로 변환하여 저장"""
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(excel_file, engine='openpyxl')
        
        # DataFrame을 딕셔너리 리스트로 변환
        questions = df.to_dict('records')
        
        # JSON 구조 생성
        data = {'raycast_questions': questions}
        
        # JSON 파일로 저장
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 엑셀 데이터가 {json_file}로 저장되었습니다.")
        
    except FileNotFoundError:
        print(f"❌ {excel_file} 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def load_questions_from_excel(excel_file='questions.xlsx'):
    """엑셀 파일에서 문제 데이터를 직접 로드"""
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        questions = df.to_dict('records')
        return questions
    except FileNotFoundError:
        print(f"❌ {excel_file} 파일을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

if __name__ == '__main__':
    # 사용 예시
    print("1. JSON → Excel 변환")
    json_to_excel()
    
    print("\n2. Excel → JSON 변환")
    excel_to_json()
    
    print("\n3. Excel에서 직접 데이터 로드")
    questions = load_questions_from_excel()
    if questions:
        print(f"✅ {len(questions)}개의 문제를 로드했습니다.")
        print(f"첫 번째 문제: {questions[0]['title']}")