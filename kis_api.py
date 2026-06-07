#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS (한국투자증권) Open API 연동 모듈"""
import os
import time
import threading
import requests

_APP_KEY    = os.environ.get('KIS_APP_KEY', '')
_APP_SECRET = os.environ.get('KIS_APP_SECRET', '')

# KIS_MODE=paper 로 설정하면 모의투자 서버 사용
_BASE = {
    'real':  'https://openapi.koreainvestment.com:9443',
    'paper': 'https://openapivts.koreainvestment.com:29443',
}
_MODE = os.environ.get('KIS_MODE', 'real')

def _base():
    return _BASE.get(_MODE, _BASE['real'])

_token_cache = {'token': None, 'expires_at': 0.0}
_token_lock  = threading.Lock()
_TOKEN_FILE  = os.path.join(os.path.dirname(__file__), '.kis_token_cache')


def _load_token_cache():
    try:
        import json
        with open(_TOKEN_FILE, 'r') as f:
            d = json.load(f)
        if time.time() < d.get('expires_at', 0):
            _token_cache['token']      = d['token']
            _token_cache['expires_at'] = d['expires_at']
    except Exception:
        pass


def _save_token_cache():
    try:
        import json
        with open(_TOKEN_FILE, 'w') as f:
            json.dump({'token': _token_cache['token'], 'expires_at': _token_cache['expires_at']}, f)
    except Exception:
        pass


_load_token_cache()


def get_token():
    # KIS는 동일 appkey에 대한 동시 토큰 발급 요청을 403으로 거부하므로
    # 락으로 직렬화해 실제 HTTP 요청은 한 번만 나가도록 한다.
    with _token_lock:
        now = time.time()
        if _token_cache['token'] and now < _token_cache['expires_at']:
            return _token_cache['token']

        if not _APP_KEY or not _APP_SECRET:
            print("  KIS 키 없음 (KIS_APP_KEY / KIS_APP_SECRET)")
            return None

        try:
            r = requests.post(
                f'{_base()}/oauth2/tokenP',
                json={
                    'grant_type': 'client_credentials',
                    'appkey':     _APP_KEY,
                    'appsecret':  _APP_SECRET,
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            token = data.get('access_token')
            if not token:
                print(f"  KIS 토큰 발급 실패: {data.get('msg1', data)}")
                return None
            expires_in = int(data.get('expires_in', 86400))
            _token_cache['token']      = token
            _token_cache['expires_at'] = now + expires_in - 300
            _save_token_cache()
            print("  KIS 토큰 발급 성공")
            return token
        except Exception as e:
            print(f"  KIS 토큰 오류: {e}")
            return None


def _headers(token, tr_id):
    return {
        'Authorization': f'Bearer {token}',
        'appkey':        _APP_KEY,
        'appsecret':     _APP_SECRET,
        'tr_id':         tr_id,
        'Content-Type':  'application/json; charset=utf-8',
    }


def _ok(resp_json):
    return resp_json.get('rt_cd') == '0'


def get_index_price(token, code):
    """지수 현재가 조회. code: '0001'=KOSPI, '1001'=KOSDAQ"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/inquire-index-price',
            headers=_headers(token, 'FHPUP02100000'),
            params={
                'FID_COND_MRKT_DIV_CODE': 'U',
                'FID_INPUT_ISCD':         code,
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 지수 [{code}] 오류: {d.get('msg1')}")
            return None
        out  = d.get('output', {})
        curr = float(out.get('bstp_nmix_prpr', 0) or 0)
        chg  = float(out.get('bstp_nmix_prdy_vrss', 0) or 0)
        pct  = float(out.get('bstp_nmix_prdy_ctrt', 0) or 0)
        return {'val': curr, 'chg': chg, 'pct': pct, 'ok': curr > 0}
    except Exception as e:
        print(f"  KIS 지수 오류 [{code}]: {e}")
        return None


def get_volume_ranking(token, top_n=5):
    """거래대금 기준 상위 종목 조회 (KOSPI+KOSDAQ)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/volume-rank',
            headers=_headers(token, 'FHPST01710000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'J',
                'FID_COND_SCR_DIV_CODE':   '20171',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '0',
                'FID_BLNG_CLS_CODE':       '1',   # 1 = 거래대금 기준
                'FID_TRGT_CLS_CODE':       '111111111',
                'FID_TRGT_EXLS_CLS_CODE':  '000000',
                'FID_INPUT_PRICE_1':       '',
                'FID_INPUT_PRICE_2':       '',
                'FID_VOL_CNT':             '',
                'FID_INPUT_DATE_1':        '',
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 거래대금 순위 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', [])[:top_n]:
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       float(item.get('stck_prpr', 0) or 0),
                'ChagesRatio': float(item.get('prdy_ctrt', 0) or 0),
                'Amount':      float(item.get('acml_tr_pbmn', 0) or 0),
                'Market':      'KIS',
            })
        return result
    except Exception as e:
        print(f"  KIS 거래대금 순위 오류: {e}")
        return []


def get_fluctuation_ranking(token, top_n=5):
    """등락률 기준 상위 종목 조회 (상한가 제외)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/ranking/fluctuation',
            headers=_headers(token, 'FHPST01700000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'J',
                'FID_COND_SCR_DIV_CODE':   '20170',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '0',   # 0 = 상승률
                'FID_BLNG_CLS_CODE':       '0',
                'FID_TRGT_CLS_CODE':       '0',
                'FID_TRGT_EXLS_CLS_CODE':  '0',
                'FID_INPUT_PRICE_1':       '',
                'FID_INPUT_PRICE_2':       '',
                'FID_VOL_CNT':             '100000',
                'FID_INPUT_DATE_1':        '',
                'FID_RANK_SORT_CLS_CODE':  '0',   # 0 = 상승률 내림차순
                'FID_INPUT_CNT_1':         '0',
                'FID_PRC_CLS_CODE':        '0',   # 0 = 전체
                'FID_RSFL_RATE1':          '',
                'FID_RSFL_RATE2':          '',
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 등락률 순위 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', []):
            pct = float(item.get('prdy_ctrt', 0) or 0)
            if pct <= 0 or pct > 30:
                continue
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       float(item.get('stck_prpr', 0) or 0),
                'ChagesRatio': pct,
                'Amount':      float(item.get('acml_tr_pbmn', 0) or 0),
                'Market':      'KIS',
            })
            if len(result) >= top_n:
                break
        return result
    except Exception as e:
        print(f"  KIS 등락률 순위 오류: {e}")
        return []


KR_SECTORS = [
    ('0013', '전기전자'),
    ('0015', '자동차'),
    ('0021', '금융'),
    ('0009', '바이오'),
    ('0008', '화학'),
    ('0011', '철강'),
    ('0018', '건설'),
    ('0017', '에너지'),
]


def get_decline_ranking(token, top_n=5):
    """하락률 기준 상위 종목 조회 (하한가 제외)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/ranking/fluctuation',
            headers=_headers(token, 'FHPST01700000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'J',
                'FID_COND_SCR_DIV_CODE':   '20170',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '1',   # 1 = 하락률
                'FID_BLNG_CLS_CODE':       '0',
                'FID_TRGT_CLS_CODE':       '0',
                'FID_TRGT_EXLS_CLS_CODE':  '0',
                'FID_INPUT_PRICE_1':       '',
                'FID_INPUT_PRICE_2':       '',
                'FID_VOL_CNT':             '100000',
                'FID_INPUT_DATE_1':        '',
                'FID_RANK_SORT_CLS_CODE':  '0',
                'FID_INPUT_CNT_1':         '0',
                'FID_PRC_CLS_CODE':        '0',
                'FID_RSFL_RATE1':          '',
                'FID_RSFL_RATE2':          '',
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 급락주 순위 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', []):
            pct = float(item.get('prdy_ctrt', 0) or 0)
            if pct >= 0 or pct < -30:
                continue
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       float(item.get('stck_prpr', 0) or 0),
                'ChagesRatio': pct,
                'Amount':      float(item.get('acml_tr_pbmn', 0) or 0),
                'Market':      'KIS',
            })
            if len(result) >= top_n:
                break
        return result
    except Exception as e:
        print(f"  KIS 급락주 순위 오류: {e}")
        return []


def get_foreign_net_buy_ranking(token, top_n=5):
    """외국인 순매수 기준 상위 종목 (국내기관_외국인 매매종목가집계)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/foreign-institution-total',
            headers=_headers(token, 'FHPTJ04400000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'V',
                'FID_COND_SCR_DIV_CODE':   '16449',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '1',   # 1=금액정렬
                'FID_RANK_SORT_CLS_CODE':  '0',   # 0=순매수상위
                'FID_ETC_CLS_CODE':        '1',   # 1=외국인
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 외국인 순매수 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', [])[:top_n]:
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       float(item.get('stck_prpr', 0) or 0),
                'ChagesRatio': float(item.get('prdy_ctrt', 0) or 0),
                'Amount':      float(item.get('frgn_ntby_tr_pbmn', 0) or 0),
                'Market':      'KIS',
            })
        return result
    except Exception as e:
        print(f"  KIS 외국인 순매수 오류: {e}")
        return []


def get_institutional_net_buy_ranking(token, top_n=5):
    """기관 순매수 기준 상위 종목 (국내기관_외국인 매매종목가집계)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/foreign-institution-total',
            headers=_headers(token, 'FHPTJ04400000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'V',
                'FID_COND_SCR_DIV_CODE':   '16449',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '1',   # 1=금액정렬
                'FID_RANK_SORT_CLS_CODE':  '0',   # 0=순매수상위
                'FID_ETC_CLS_CODE':        '2',   # 2=기관계
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 기관 순매수 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', [])[:top_n]:
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       float(item.get('stck_prpr', 0) or 0),
                'ChagesRatio': float(item.get('prdy_ctrt', 0) or 0),
                'Amount':      float(item.get('orgn_ntby_tr_pbmn', 0) or 0),
                'Market':      'KIS',
            })
        return result
    except Exception as e:
        print(f"  KIS 기관 순매수 오류: {e}")
        return []


def get_52week_high(token, top_n=5):
    """52주 신고가 근접 종목 상위 (국내주식 신고_신저근접종목 상위)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/ranking/near-new-highlow',
            headers=_headers(token, 'FHPST01870000'),
            params={
                'FID_APLY_RANG_VOL':       '0',
                'FID_COND_MRKT_DIV_CODE':  'J',
                'FID_COND_SCR_DIV_CODE':   '20187',
                'FID_DIV_CLS_CODE':        '0',
                'FID_INPUT_CNT_1':         '0',
                'FID_INPUT_CNT_2':         '100',
                'FID_PRC_CLS_CODE':        '0',   # 0=신고근접
                'FID_INPUT_ISCD':          '0000',
                'FID_TRGT_CLS_CODE':       '0',
                'FID_TRGT_EXLS_CLS_CODE':  '0',
                'FID_APLY_RANG_PRC_1':     '0',
                'FID_APLY_RANG_PRC_2':     '1000000',
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            print(f"  KIS 신고가 오류: {d.get('msg1')}")
            return []
        result = []
        for item in d.get('output', [])[:top_n]:
            close = float(item.get('stck_prpr', 0) or 0)
            vol   = float(item.get('acml_vol', 0) or 0)
            result.append({
                'Name':        item.get('hts_kor_isnm', ''),
                'Close':       close,
                'ChagesRatio': float(item.get('prdy_ctrt', 0) or 0),
                'Amount':      close * vol,  # 거래대금 필드가 없어 현재가×거래량으로 근사
                'Market':      'KIS',
            })
        return result
    except Exception as e:
        print(f"  KIS 신고가 오류: {e}")
        return []


def get_kr_sector_data(token):
    """KOSPI 주요 업종별 등락률 조회. 반환: [{'name': str, 'pct': float}, ...]"""
    results = []
    for code, name in KR_SECTORS:
        try:
            r = requests.get(
                f'{_base()}/uapi/domestic-stock/v1/quotations/inquire-index-price',
                headers=_headers(token, 'FHPUP02100000'),
                params={'FID_COND_MRKT_DIV_CODE': 'U', 'FID_INPUT_ISCD': code},
                timeout=8,
            )
            r.raise_for_status()
            d = r.json()
            if not _ok(d):
                results.append({'name': name, 'pct': 0.0})
                continue
            out = d.get('output', {})
            pct = float(out.get('bstp_nmix_prdy_ctrt', 0) or 0)
            results.append({'name': name, 'pct': round(pct, 2)})
        except Exception as e:
            print(f"  KIS 업종 오류 [{name}]: {e}")
            results.append({'name': name, 'pct': 0.0})
    return results


_ETF_PREFIXES = ('KODEX', 'TIGER', 'KINDEX', 'ARIRANG', 'HANARO', 'KOSEF', 'SOL', 'ACE', 'TIMEFOLIO', 'KB')


def get_etf_volume_ranking(token, top_n=5):
    """거래대금 상위 ETF 조회 (ETF 이름 접두어로 필터링)"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/volume-rank',
            headers=_headers(token, 'FHPST01710000'),
            params={
                'FID_COND_MRKT_DIV_CODE':  'J',
                'FID_COND_SCR_DIV_CODE':   '20171',
                'FID_INPUT_ISCD':          '0000',
                'FID_DIV_CLS_CODE':        '0',
                'FID_BLNG_CLS_CODE':       '1',
                'FID_TRGT_CLS_CODE':       '111111111',
                'FID_TRGT_EXLS_CLS_CODE':  '000000',
                'FID_INPUT_PRICE_1':       '',
                'FID_INPUT_PRICE_2':       '',
                'FID_VOL_CNT':             '',
                'FID_INPUT_DATE_1':        '',
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            return []
        result = []
        for item in d.get('output', []):
            name = item.get('hts_kor_isnm', '')
            if not any(name.startswith(p) for p in _ETF_PREFIXES):
                continue
            amt = float(item.get('acml_tr_pbmn', 0) or 0)
            if amt <= 0:
                continue
            result.append({
                'name': name,
                'val':  float(item.get('stck_prpr', 0) or 0),
                'pct':  float(item.get('prdy_ctrt', 0) or 0),
                'amt':  amt,
            })
            if len(result) >= top_n:
                break
        return result
    except Exception as e:
        print(f"  KIS ETF 거래대금 오류: {e}")
        return []


def get_stock_price(token, ticker):
    """개별 종목 현재가 조회. ticker: '005930' 형식 6자리"""
    try:
        r = requests.get(
            f'{_base()}/uapi/domestic-stock/v1/quotations/inquire-price',
            headers=_headers(token, 'FHKST01010100'),
            params={
                'FID_COND_MRKT_DIV_CODE': 'J',
                'FID_INPUT_ISCD':         ticker,
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not _ok(d):
            return None
        out  = d.get('output', {})
        curr = float(out.get('stck_prpr', 0) or 0)
        chg  = float(out.get('prdy_vrss', 0) or 0)
        pct  = float(out.get('prdy_ctrt', 0) or 0)
        return {'val': curr, 'chg': chg, 'pct': pct, 'ok': curr > 0}
    except Exception as e:
        print(f"  KIS 종목가 오류 [{ticker}]: {e}")
        return None
