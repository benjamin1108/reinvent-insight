/**
 * CacheManager 单元测试
 * 使用简单的测试框架进行测试
 */

// 简单的测试框架
const test = (name, fn) => {
  try {
    fn();
    console.log(`✅ ${name}`);
    return true;
  } catch (error) {
    console.error(`❌ ${name}: ${error.message}`);
    return false;
  }
};

const assert = {
  equal: (actual, expected, message) => {
    if (actual !== expected) {
      throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
  },
  notEqual: (actual, expected, message) => {
    if (actual === expected) {
      throw new Error(message || `Expected not ${expected}`);
    }
  },
  ok: (value, message) => {
    if (!value) {
      throw new Error(message || `Expected truthy value`);
    }
  },
  null: (value, message) => {
    if (value !== null) {
      throw new Error(message || `Expected null, got ${value}`);
    }
  }
};

// 测试套件
function runCacheManagerTests() {
  console.group('CacheManager 单元测试');
  
  // 清空缓存
  CacheManager.clear();
  CacheManager.resetStats();
  
  const results = [];
  
  // 测试1: 基本存取
  results.push(test('应该能够存储和获取数据', () => {
    const data = { name: 'test', value: 123 };
    CacheManager.set('test-key', data);
    const retrieved = CacheManager.get('test-key');
    assert.equal(retrieved.name, 'test');
    assert.equal(retrieved.value, 123);
  }));
  
  // 测试2: 缓存未命中
  results.push(test('不存在的键应该返回null', () => {
    const result = CacheManager.get('non-existent-key');
    assert.null(result);
  }));
  
  // 测试3: 缓存统计
  results.push(test('应该正确统计缓存命中和未命中', () => {
    CacheManager.clear();
    CacheManager.resetStats();
    
    CacheManager.set('key1', { data: 'test' });
    CacheManager.get('key1'); // 命中
    CacheManager.get('key2'); // 未命中
    
    const stats = CacheManager.getStats();
    assert.equal(stats.hits, 1);
    assert.equal(stats.misses, 1);
    assert.equal(stats.hitRate, 0.5);
  }));
  
  // 测试4: 版本检查
  results.push(test('应该支持版本检查', () => {
    CacheManager.set('versioned-key', { data: 'test' }, { version: '1.0.0' });
    const isValid = CacheManager.checkVersion('versioned-key', '1.0.0');
    const isInvalid = CacheManager.checkVersion('versioned-key', '2.0.0');
    assert.ok(isValid);
    assert.ok(!isInvalid);
  }));
  
  // 测试5: 清除缓存
  results.push(test('应该能够清除单个缓存', () => {
    CacheManager.set('key-to-clear', { data: 'test' });
    CacheManager.clear('key-to-clear');
    const result = CacheManager.get('key-to-clear');
    assert.null(result);
  }));
  
  // 测试6: 清除所有缓存
  results.push(test('应该能够清除所有缓存', () => {
    CacheManager.set('key1', { data: 'test1' });
    CacheManager.set('key2', { data: 'test2' });
    CacheManager.clear();
    const stats = CacheManager.getStats();
    assert.equal(stats.entryCount, 0);
  }));
  
  // 测试7: 缓存条目详情
  results.push(test('应该能够获取缓存条目详情', () => {
    CacheManager.set('detail-key', { data: 'test' }, { version: '1.0.0' });
    const entry = CacheManager.getEntry('detail-key');
    assert.ok(entry);
    assert.equal(entry.version, '1.0.0');
    assert.ok(entry.valid);
  }));
  
  // 测试8: 导出缓存数据
  results.push(test('应该能够导出缓存数据', () => {
    CacheManager.clear();
    CacheManager.set('export-key', { data: 'test' });
    const exported = CacheManager.export();
    assert.ok(exported.entries);
    assert.ok(exported.stats);
    assert.ok(exported.entries['export-key']);
  }));
  
  const passed = results.filter(r => r).length;
  const total = results.length;
  
  console.groupEnd();
  console.log(`\n📊 测试结果: ${passed}/${total} 通过`);
  
  return { passed, total, success: passed === total };
}

// 如果在浏览器环境中，自动运行测试
if (typeof window !== 'undefined' && window.CacheManager) {
  runCacheManagerTests();
}

// 导出测试函数
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { runCacheManagerTests };
}
