#!/usr/bin/env python3
"""
测试API是否能正确返回中英文标题
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:8001"

def test_public_summaries():
    """测试公共摘要列表API"""
    print("测试 /api/public/summaries 端点...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/public/summaries")
        response.raise_for_status()
        
        data = response.json()
        summaries = data.get("summaries", [])
        
        print(f"\n找到 {len(summaries)} 个摘要文件")
        
        # 显示前3个摘要的标题信息
        for i, summary in enumerate(summaries[:3]):
            print(f"\n摘要 {i+1}:")
            print(f"  文件名: {summary.get('filename', 'N/A')}")
            print(f"  中文标题: {summary.get('title_cn', 'N/A')}")
            print(f"  英文标题: {summary.get('title_en', 'N/A')}")
            print(f"  是否reinvent: {summary.get('is_reinvent', False)}")
            if summary.get('is_reinvent'):
                print(f"  课程代码: {summary.get('course_code', 'N/A')}")
                print(f"  级别: {summary.get('level', 'N/A')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return False
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def test_get_summary(filename):
    """测试获取单个摘要API"""
    print(f"\n测试 /api/public/summaries/{filename} 端点...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/public/summaries/{filename}")
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n摘要详情:")
        print(f"  文件名: {data.get('filename', 'N/A')}")
        print(f"  中文标题: {data.get('title_cn', 'N/A')}")
        print(f"  英文标题: {data.get('title_en', 'N/A')}")
        print(f"  视频URL: {data.get('video_url', 'N/A')}")
        print(f"  内容长度: {len(data.get('content', ''))} 字符")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return False
    except Exception as e:
        print(f"测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试API...")
    print(f"API地址: {BASE_URL}")
    print("-" * 50)
    
    # 测试摘要列表
    if test_public_summaries():
        print("\n✅ 摘要列表API测试通过")
        
        # 获取第一个摘要的文件名进行详情测试
        response = requests.get(f"{BASE_URL}/api/public/summaries")
        summaries = response.json().get("summaries", [])
        
        if summaries:
            first_file = summaries[0].get("filename")
            if first_file:
                if test_get_summary(first_file):
                    print("\n✅ 摘要详情API测试通过")
                else:
                    print("\n❌ 摘要详情API测试失败")
        else:
            print("\n⚠️  没有找到摘要文件，跳过详情测试")
    else:
        print("\n❌ 摘要列表API测试失败")
    
    print("\n" + "-" * 50)
    print("测试完成！")

if __name__ == "__main__":
    main() 