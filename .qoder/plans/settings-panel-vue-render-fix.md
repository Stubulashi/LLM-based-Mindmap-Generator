# 设置面板 Vue 模板渲染异常修复计划

## 上下文

`index.html` 中的设置面板弹窗（约第 415-508 行）使用 Vue 3 模板语法（`{{ t('preferences') }}`、`{{ settings.language === 'zh' ? '少' : 'Low' }}` 等）进行渲染。用户打开偏好设置弹窗时，这些插值表达式显示为原始模板文本而非实际值，导致整个设置面板不可用。

## 根因

**文件**: `/home/akku/ai-mindmap-agent/index.html`  
**位置**: 第 2137 行，Vue `setup()` 函数的 `return` 语句中

```javascript
showDefinition, closeDefinition, startDragPopup
// C: Wikipedia 定义截断相关
// E: Wikipedia definition truncation helpers
truncatedWikiDefinition, wikiDefinitionIsTruncated, wikiDefinitionFullLength
```

`startDragPopup` 和 `truncatedWikiDefinition` 之间**缺少逗号分隔符**。JavaScript 对象字面量中属性必须以逗号分隔，此处缺失逗号导致 `SyntaxError`，整个 `<script>` 块解析失败。因此 `createApp({...}).mount('#app')` 从未执行，Vue 实例未初始化，所有 `{{ }}` 插值表达式作为纯文本显示。

其他方面（Vue 版本 `vue@3/dist/vue.global.js` 包含模板编译器、`t()` 函数正确定义在 `setup()` 内、`locales` 对象完整）均无问题。

## 修复方案

在第 2137 行 `startDragPopup` 后添加逗号。

**改动前**:
```
showDefinition, closeDefinition, startDragPopup
// C: Wikipedia 定义截断相关
// E: Wikipedia definition truncation helpers
truncatedWikiDefinition, wikiDefinitionIsTruncated, wikiDefinitionFullLength
```

**改动后**:
```
showDefinition, closeDefinition, startDragPopup,
// C: Wikipedia 定义截断相关
// E: Wikipedia definition truncation helpers
truncatedWikiDefinition, wikiDefinitionIsTruncated, wikiDefinitionFullLength
```

## 验证方式

1. 在浏览器中打开页面，点击齿轮图标打开设置弹窗
2. 确认所有标签文案正确渲染（"全局参数设置"、"界面语言"、"全局缩放"等）
3. 确认语言切换、字体选择、尺寸按钮、标注密度、定义详细度、同步/滚动开关均可正常交互
4. 确认浏览器控制台无 JavaScript 语法错误
