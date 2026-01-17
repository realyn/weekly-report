<script setup>
import { ref, computed, onMounted } from 'vue'
import { projectsApi } from '../../api/projects'
import { summaryApi } from '../../api/summary'
import { ElMessage, ElMessageBox } from 'element-plus'

// 项目数据
const projects = ref([])
const categories = ref([])
const loading = ref(false)

// 待审核项目
const pendingProjects = ref([])
const rejectedProjects = ref([])

// 展开状态
const expandedProjects = ref(new Set())

// 弹窗状态
const projectDialogVisible = ref(false)
const editingProject = ref(null)
const projectForm = ref({
  name: '',
  category: '其他',
  description: '',
  aliases: [],
  sub_items: []
})
const aliasInput = ref('')
const editingAliasIndex = ref(-1)
const editingAliasValue = ref('')

// 防止拖拽选择文字时误关闭弹窗
const mouseDownOnOverlay = ref(false)
const handleOverlayMouseDown = (e) => {
  mouseDownOnOverlay.value = e.target === e.currentTarget
}
const handleOverlayClick = (e, closeFunc) => {
  if (e.target === e.currentTarget && mouseDownOnOverlay.value) {
    closeFunc()
  }
  mouseDownOnOverlay.value = false
}

// 子项目弹窗
const subItemDialogVisible = ref(false)
const editingSubItem = ref(null)
const subItemParent = ref(null)
const subItemForm = ref({
  name: '',
  description: ''
})

// 类别管理弹窗
const categoryDialogVisible = ref(false)
const newCategoryName = ref('')

// 审核弹窗
const approveDialogVisible = ref(false)
const approvingProject = ref(null)
const approveCategory = ref('其他')

// 合并弹窗
const mergeDialogVisible = ref(false)
const mergingProject = ref(null)
const mergeTarget = ref('')

// 分析触发
const analysisYear = ref(new Date().getFullYear())
const analysisWeek = ref(1)
const analyzing = ref(false)

// 获取当前ISO周
const getCurrentISOWeek = () => {
  const now = new Date()
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  d.setDate(d.getDate() + 4 - (d.getDay() || 7))
  const yearStart = new Date(d.getFullYear(), 0, 1)
  return Math.ceil((((d - yearStart) / 86400000) + 1) / 7)
}

analysisWeek.value = getCurrentISOWeek()

// 按类别分组的项目
const projectsByCategory = computed(() => {
  const groups = {}
  for (const project of projects.value) {
    const cat = project.category || '其他'
    if (!groups[cat]) {
      groups[cat] = []
    }
    groups[cat].push(project)
  }
  // 按类别名称排序
  const sorted = {}
  Object.keys(groups).sort().forEach(key => {
    sorted[key] = groups[key]
  })
  return sorted
})

// 加载数据
const fetchProjects = async () => {
  loading.value = true
  try {
    const [projectsRes, categoriesRes, pendingRes, rejectedRes] = await Promise.all([
      projectsApi.getProjectsDetail(),
      projectsApi.getCategories(),
      projectsApi.getPending(),
      projectsApi.getRejected()
    ])
    projects.value = projectsRes.data || []
    categories.value = categoriesRes.data || []
    pendingProjects.value = pendingRes.data || []
    rejectedProjects.value = rejectedRes.data || []
  } catch (e) {
    console.error('加载失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchProjects)

// 触发分析
const triggerAnalysis = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要重新分析 ${analysisYear.value}年第${analysisWeek.value}周 的项目分类吗？`,
      '确认分析'
    )
    analyzing.value = true
    await summaryApi.triggerAnalysis(analysisYear.value, analysisWeek.value)
    ElMessage.success(`${analysisYear.value}年第${analysisWeek.value}周 项目分析完成`)
    fetchProjects()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('分析失败')
    }
  } finally {
    analyzing.value = false
  }
}

// 切换展开
const toggleExpand = (projectName) => {
  if (expandedProjects.value.has(projectName)) {
    expandedProjects.value.delete(projectName)
  } else {
    expandedProjects.value.add(projectName)
  }
}

// 打开项目弹窗
const openProjectDialog = (project = null) => {
  editingProject.value = project
  if (project) {
    projectForm.value = {
      name: project.name,
      category: project.category || '其他',
      description: project.description || '',
      aliases: [...(project.aliases || [])],
      sub_items: (project.sub_items || []).map(s => typeof s === 'string' ? { name: s, description: '' } : { ...s })
    }
  } else {
    projectForm.value = {
      name: '',
      category: '其他',
      description: '',
      aliases: [],
      sub_items: []
    }
  }
  aliasInput.value = ''
  editingAliasIndex.value = -1
  editingAliasValue.value = ''
  projectDialogVisible.value = true
}

// 添加别名
const addAlias = () => {
  const alias = aliasInput.value.trim()
  if (alias && !projectForm.value.aliases.includes(alias)) {
    projectForm.value.aliases.push(alias)
    aliasInput.value = ''
  }
}

// 删除别名
const removeAlias = (index) => {
  projectForm.value.aliases.splice(index, 1)
}

// 开始编辑别名
const startEditAlias = (index) => {
  editingAliasIndex.value = index
  editingAliasValue.value = projectForm.value.aliases[index]
}

// 保存编辑的别名
const saveEditAlias = () => {
  if (editingAliasIndex.value >= 0 && editingAliasValue.value.trim()) {
    projectForm.value.aliases[editingAliasIndex.value] = editingAliasValue.value.trim()
  }
  cancelEditAlias()
}

// 取消编辑别名
const cancelEditAlias = () => {
  editingAliasIndex.value = -1
  editingAliasValue.value = ''
}

// 保存项目
const handleSaveProject = async () => {
  if (!projectForm.value.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }

  try {
    if (editingProject.value) {
      if (editingProject.value.name !== projectForm.value.name.trim()) {
        await projectsApi.renameProject(editingProject.value.name, projectForm.value.name.trim())
      }
      await projectsApi.updateProject(projectForm.value.name.trim(), {
        category: projectForm.value.category,
        description: projectForm.value.description,
        aliases: projectForm.value.aliases,
        sub_items: projectForm.value.sub_items
      })
      ElMessage.success('项目更新成功')
    } else {
      await projectsApi.createProject({
        name: projectForm.value.name.trim(),
        category: projectForm.value.category,
        description: projectForm.value.description,
        aliases: projectForm.value.aliases,
        sub_items: projectForm.value.sub_items
      })
      ElMessage.success('项目创建成功')
    }
    projectDialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 删除项目
const handleDeleteProject = async (project) => {
  await ElMessageBox.confirm(
    `确定删除项目「${project.name}」吗？此操作不可恢复。`,
    '确认删除',
    { type: 'warning' }
  )
  try {
    await projectsApi.deleteProject(project.name)
    ElMessage.success(`已删除项目「${project.name}」`)
    fetchProjects()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 打开子项目弹窗
const openSubItemDialog = (project, subItem = null) => {
  subItemParent.value = project
  editingSubItem.value = subItem
  if (subItem) {
    subItemForm.value = {
      name: subItem.name,
      description: subItem.description || ''
    }
  } else {
    subItemForm.value = {
      name: '',
      description: ''
    }
  }
  subItemDialogVisible.value = true
}

// 保存子项目
const handleSaveSubItem = async () => {
  if (!subItemForm.value.name.trim()) {
    ElMessage.warning('请输入子项目名称')
    return
  }

  try {
    if (editingSubItem.value) {
      await projectsApi.updateSubItem(
        subItemParent.value.name,
        editingSubItem.value.name,
        {
          name: subItemForm.value.name.trim(),
          description: subItemForm.value.description
        }
      )
      ElMessage.success('子项目更新成功')
    } else {
      await projectsApi.addSubItem(
        subItemParent.value.name,
        subItemForm.value.name.trim(),
        subItemForm.value.description
      )
      ElMessage.success('子项目添加成功')
    }
    subItemDialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 删除子项目
const handleDeleteSubItem = async (project, subItem) => {
  await ElMessageBox.confirm(
    `确定删除子项目「${subItem.name}」吗？`,
    '确认删除'
  )
  try {
    await projectsApi.removeSubItem(project.name, subItem.name)
    ElMessage.success(`已删除子项目「${subItem.name}」`)
    fetchProjects()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 类别管理
const openCategoryDialog = () => {
  newCategoryName.value = ''
  categoryDialogVisible.value = true
}

const handleAddCategory = async () => {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入类别名称')
    return
  }
  try {
    await projectsApi.addCategory(newCategoryName.value.trim())
    ElMessage.success(`已添加类别「${newCategoryName.value.trim()}」`)
    newCategoryName.value = ''
    fetchProjects()
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

const handleRemoveCategory = async (category) => {
  const usingProjects = projects.value.filter(p => p.category === category)
  if (usingProjects.length > 0) {
    ElMessage.warning(`有 ${usingProjects.length} 个项目使用此类别，请先修改`)
    return
  }

  await ElMessageBox.confirm(`确定删除类别「${category}」吗？`, '确认删除')
  try {
    await projectsApi.removeCategory(category)
    ElMessage.success(`已删除类别「${category}」`)
    fetchProjects()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 待审核项目管理
const openApproveDialog = (project) => {
  approvingProject.value = project
  approveCategory.value = project.suggested_category || '其他'
  approveDialogVisible.value = true
}

const handleApprove = async () => {
  if (!approvingProject.value) return
  try {
    await projectsApi.approve(approvingProject.value.name, approveCategory.value)
    ElMessage.success(`已将「${approvingProject.value.name}」添加到「${approveCategory.value}」类别`)
    approveDialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const openMergeDialog = (project) => {
  mergingProject.value = project
  mergeTarget.value = ''
  mergeDialogVisible.value = true
}

const handleMerge = async () => {
  if (!mergingProject.value || !mergeTarget.value) return
  try {
    await projectsApi.merge(mergingProject.value.name, mergeTarget.value)
    ElMessage.success(`已将「${mergingProject.value.name}」作为「${mergeTarget.value}」的别名`)
    mergeDialogVisible.value = false
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleReject = async (project) => {
  await ElMessageBox.confirm(
    `确定拒绝「${project.name}」吗？拒绝后将加入黑名单，不再提示。`,
    '确认拒绝'
  )
  try {
    await projectsApi.reject(project.name)
    ElMessage.success(`已将「${project.name}」加入黑名单`)
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleRemoveFromRejected = async (name) => {
  await ElMessageBox.confirm(`确定将「${name}」从黑名单移除吗？`, '确认移除')
  try {
    await projectsApi.removeFromRejected(name)
    ElMessage.success(`已将「${name}」从黑名单移除`)
    fetchProjects()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 显示项目归属设置（从 localStorage 读取）
const showProjectAttribution = ref(localStorage.getItem('showProjectAttribution') === 'true')

// 保存显示项目归属设置
const saveProjectAttributionSetting = () => {
  localStorage.setItem('showProjectAttribution', showProjectAttribution.value.toString())
}

// 重建向量索引
const rebuildingEmbeddings = ref(false)
const handleRebuildEmbeddings = async () => {
  await ElMessageBox.confirm(
    '确定重建项目向量索引吗？这将重新计算所有项目的语义向量。',
    '确认重建'
  )
  try {
    rebuildingEmbeddings.value = true
    await projectsApi.rebuildEmbeddings()
    ElMessage.success('向量索引重建完成')
  } catch (e) {
    ElMessage.error('重建失败')
  } finally {
    rebuildingEmbeddings.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">项目管理</h1>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="openCategoryDialog">类别管理</button>
          <button class="btn btn-secondary" @click="handleRebuildEmbeddings" :disabled="rebuildingEmbeddings">
            {{ rebuildingEmbeddings ? '重建中...' : '重建索引' }}
          </button>
          <button class="btn btn-primary" @click="openProjectDialog()">添加项目</button>
        </div>
      </div>

      <!-- 显示设置 -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="system-section">
          <div class="section-title">显示设置</div>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-name">显示项目归属</span>
              <span class="setting-desc">在周报汇总页面的工作条目后显示所属项目名称</span>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="showProjectAttribution" @change="saveProjectAttributionSetting">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- 项目分类分析 -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="system-section">
          <div class="section-title">项目分类分析</div>
          <p class="section-desc">手动触发指定周次的LLM项目分类分析，用于更新或修正项目归类结果</p>
          <div class="analysis-form">
            <div class="form-inline">
              <input type="number" v-model.number="analysisYear" min="2020" max="2030" class="form-input-small" />
              <span class="form-text">年 第</span>
              <input type="number" v-model.number="analysisWeek" min="1" max="53" class="form-input-small" />
              <span class="form-text">周</span>
              <button class="btn btn-primary" @click="triggerAnalysis" :disabled="analyzing">
                {{ analyzing ? '分析中...' : '触发分析' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 待审核项目 -->
      <div v-if="pendingProjects.length" class="section-block">
        <div class="section-header">
          <h2 class="section-title-large">待审核项目</h2>
          <span class="badge warning">{{ pendingProjects.length }}</span>
        </div>
        <div class="card">
          <div class="pending-list">
            <div class="pending-item" v-for="project in pendingProjects" :key="project.name">
              <div class="pending-info">
                <span class="pending-name">{{ project.name }}</span>
                <span class="pending-meta">
                  首次出现: {{ project.first_seen }} |
                  提及次数: {{ project.mentions }} |
                  置信度: {{ (project.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="pending-actions">
                <button class="action-btn approve" @click="openApproveDialog(project)">确认添加</button>
                <button class="action-btn merge" @click="openMergeDialog(project)">合并到已有</button>
                <button class="action-btn reject" @click="handleReject(project)">拒绝</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div class="card" v-if="loading">
        <div class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>
      </div>

      <!-- 项目列表（按类别分组） -->
      <template v-else>
        <div v-for="(categoryProjects, category) in projectsByCategory" :key="category" class="category-section">
          <div class="category-header">
            <h2 class="category-title">{{ category }}</h2>
            <span class="category-count">{{ categoryProjects.length }} 个项目</span>
          </div>

          <div class="card">
            <div class="project-list">
              <div
                v-for="project in categoryProjects"
                :key="project.name"
                class="project-item"
              >
                <!-- 项目头部 -->
                <div class="project-header" @click="toggleExpand(project.name)">
                  <div class="project-main">
                    <span class="expand-icon">{{ expandedProjects.has(project.name) ? '▼' : '▶' }}</span>
                    <span class="project-name">{{ project.name }}</span>
                    <span class="project-status" :class="project.status || 'active'">
                      {{ project.status === 'archived' ? '归档' : '活跃' }}
                    </span>
                  </div>
                  <div class="project-meta">
                    <span v-if="project.aliases?.length" class="meta-item">
                      别名: {{ project.aliases.slice(0, 3).join(', ') }}{{ project.aliases.length > 3 ? '...' : '' }}
                    </span>
                    <span v-if="project.sub_items?.length" class="meta-item">
                      {{ project.sub_items.length }} 个子项目
                    </span>
                  </div>
                  <div class="project-actions" @click.stop>
                    <button class="action-btn edit" @click="openProjectDialog(project)">编辑</button>
                    <button class="action-btn delete" @click="handleDeleteProject(project)">删除</button>
                  </div>
                </div>

                <!-- 展开详情 -->
                <div v-if="expandedProjects.has(project.name)" class="project-detail">
                  <!-- 描述 -->
                  <div v-if="project.description" class="detail-section">
                    <div class="detail-label">描述</div>
                    <div class="detail-content">{{ project.description }}</div>
                  </div>

                  <!-- 别名 -->
                  <div v-if="project.aliases?.length" class="detail-section">
                    <div class="detail-label">别名</div>
                    <div class="alias-tags">
                      <span v-for="alias in project.aliases" :key="alias" class="alias-tag">
                        {{ alias }}
                      </span>
                    </div>
                  </div>

                  <!-- 子项目 -->
                  <div class="detail-section">
                    <div class="detail-header">
                      <div class="detail-label">子项目</div>
                      <button class="btn-small" @click="openSubItemDialog(project)">添加子项目</button>
                    </div>
                    <div v-if="project.sub_items?.length" class="sub-items-list">
                      <div v-for="(sub, subIndex) in project.sub_items" :key="subIndex" class="sub-item">
                        <div class="sub-item-info">
                          <span class="sub-item-name">{{ typeof sub === 'string' ? sub : sub.name }}</span>
                          <span v-if="typeof sub !== 'string' && sub.description" class="sub-item-desc">{{ sub.description }}</span>
                        </div>
                        <div class="sub-item-actions">
                          <button class="action-btn-small" @click="openSubItemDialog(project, typeof sub === 'string' ? { name: sub } : sub)">编辑</button>
                          <button class="action-btn-small delete" @click="handleDeleteSubItem(project, typeof sub === 'string' ? { name: sub } : sub)">删除</button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="empty-sub-items">
                      暂无子项目
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!projects.length && !loading" class="card">
          <div class="empty-state">
            <div class="empty-icon">📁</div>
            <p>暂无项目数据</p>
            <button class="btn btn-primary" @click="openProjectDialog()">创建第一个项目</button>
          </div>
        </div>
      </template>

      <!-- 黑名单 -->
      <div v-if="rejectedProjects.length" class="section-block" style="margin-top: 24px;">
        <div class="section-header">
          <h2 class="section-title-large">黑名单</h2>
          <span class="badge muted">{{ rejectedProjects.length }}</span>
        </div>
        <div class="card">
          <div class="rejected-list">
            <div class="rejected-item" v-for="name in rejectedProjects" :key="name">
              <span class="rejected-name">{{ name }}</span>
              <button class="action-btn-small" @click="handleRemoveFromRejected(name)">移除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 项目编辑弹窗 -->
    <div class="modal-overlay" v-if="projectDialogVisible" @mousedown="handleOverlayMouseDown" @click="handleOverlayClick($event, () => projectDialogVisible = false)">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>{{ editingProject ? '编辑项目' : '创建项目' }}</h3>
          <button class="modal-close" @click="projectDialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">项目名称 *</label>
            <input type="text" v-model="projectForm.name" class="form-input" placeholder="请输入项目名称" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">类别</label>
              <select v-model="projectForm.category" class="form-select">
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="projectForm.description" class="form-textarea" rows="2" placeholder="项目描述（可选）"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">别名</label>
            <div class="alias-input-row">
              <input
                type="text"
                v-model="aliasInput"
                class="form-input"
                placeholder="输入别名后按回车添加"
                @keyup.enter="addAlias"
              />
              <button class="btn btn-secondary btn-small-inline" @click="addAlias">添加</button>
            </div>
            <div v-if="projectForm.aliases.length" class="alias-list" style="margin-top: 8px;">
              <div v-for="(alias, index) in projectForm.aliases" :key="index" class="alias-item">
                <template v-if="editingAliasIndex === index">
                  <input
                    type="text"
                    v-model="editingAliasValue"
                    class="form-input alias-edit-input"
                    @keyup.enter="saveEditAlias"
                    @keyup.escape="cancelEditAlias"
                    autofocus
                  />
                  <button class="alias-action-btn save" @click="saveEditAlias">保存</button>
                  <button class="alias-action-btn cancel" @click="cancelEditAlias">取消</button>
                </template>
                <template v-else>
                  <span class="alias-tag">{{ alias }}</span>
                  <button class="alias-action-btn edit" @click="startEditAlias(index)">编辑</button>
                  <button class="alias-action-btn delete" @click="removeAlias(index)">删除</button>
                </template>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="projectDialogVisible = false">取消</button>
          <button class="btn btn-primary" @click="handleSaveProject">保存</button>
        </div>
      </div>
    </div>

    <!-- 子项目编辑弹窗 -->
    <div class="modal-overlay" v-if="subItemDialogVisible" @mousedown="handleOverlayMouseDown" @click="handleOverlayClick($event, () => subItemDialogVisible = false)">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>{{ editingSubItem ? '编辑子项目' : '添加子项目' }}</h3>
          <button class="modal-close" @click="subItemDialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <p class="modal-text" v-if="subItemParent">所属项目：{{ subItemParent.name }}</p>
          <div class="form-group">
            <label class="form-label">子项目名称 *</label>
            <input type="text" v-model="subItemForm.name" class="form-input" placeholder="请输入子项目名称" />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="subItemForm.description" class="form-textarea" rows="2" placeholder="子项目描述（可选）"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="subItemDialogVisible = false">取消</button>
          <button class="btn btn-primary" @click="handleSaveSubItem">保存</button>
        </div>
      </div>
    </div>

    <!-- 类别管理弹窗 -->
    <div class="modal-overlay" v-if="categoryDialogVisible" @mousedown="handleOverlayMouseDown" @click="handleOverlayClick($event, () => categoryDialogVisible = false)">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>类别管理</h3>
          <button class="modal-close" @click="categoryDialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="category-add-row">
            <input
              type="text"
              v-model="newCategoryName"
              class="form-input"
              placeholder="输入新类别名称"
              @keyup.enter="handleAddCategory"
            />
            <button class="btn btn-primary btn-small-inline" @click="handleAddCategory">添加</button>
          </div>
          <div class="category-list">
            <div v-for="cat in categories" :key="cat" class="category-item">
              <span class="category-name">{{ cat }}</span>
              <button class="action-btn-small delete" @click="handleRemoveCategory(cat)">删除</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="categoryDialogVisible = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 确认添加弹窗 -->
    <div class="modal-overlay" v-if="approveDialogVisible" @mousedown="handleOverlayMouseDown" @click="handleOverlayClick($event, () => approveDialogVisible = false)">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>确认添加项目</h3>
          <button class="modal-close" @click="approveDialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <p class="modal-text">将「{{ approvingProject?.name }}」添加为正式项目</p>
          <div class="form-group">
            <label class="form-label">选择类别</label>
            <select v-model="approveCategory" class="form-select">
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="approveDialogVisible = false">取消</button>
          <button class="btn btn-primary" @click="handleApprove">确认</button>
        </div>
      </div>
    </div>

    <!-- 合并项目弹窗 -->
    <div class="modal-overlay" v-if="mergeDialogVisible" @mousedown="handleOverlayMouseDown" @click="handleOverlayClick($event, () => mergeDialogVisible = false)">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>合并到已有项目</h3>
          <button class="modal-close" @click="mergeDialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <p class="modal-text">将「{{ mergingProject?.name }}」作为别名合并到：</p>
          <div class="form-group">
            <label class="form-label">选择目标项目</label>
            <select v-model="mergeTarget" class="form-select">
              <option value="" disabled>请选择项目</option>
              <option v-for="proj in projects" :key="proj.name" :value="proj.name">
                {{ proj.name }} ({{ proj.category }})
              </option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="mergeDialogVisible = false">取消</button>
          <button class="btn btn-primary" @click="handleMerge" :disabled="!mergeTarget">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 基础样式 */
.page-container {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f8fafc;
}

.page-content {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #7aaed8;
  color: white;
}

.btn-primary:hover {
  background: #4a9bc4;
}

.btn-primary:disabled {
  background: #a8d4ed;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.btn-secondary:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-small-inline {
  padding: 8px 14px;
  font-size: 13px;
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
  background: #7aaed8;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-small:hover {
  background: #4a9bc4;
}

/* 卡片 */
.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

/* 分区块 */
.section-block {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-left: 4px;
}

.section-title-large {
  font-size: 1.1rem;
  font-weight: 600;
  color: #334155;
  margin: 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 8px;
  border-radius: 11px;
  font-size: 12px;
  font-weight: 600;
}

.badge.warning {
  background: #fef3c7;
  color: #d97706;
}

.badge.muted {
  background: #f1f5f9;
  color: #64748b;
}

/* 类别分组 */
.category-section {
  margin-bottom: 24px;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding-left: 4px;
}

.category-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #334155;
  margin: 0;
}

.category-count {
  font-size: 13px;
  color: #94a3b8;
}

/* 项目列表 */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #f8fafc;
  cursor: pointer;
  transition: background 0.2s;
}

.project-header:hover {
  background: #f1f5f9;
}

.project-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 200px;
}

.expand-icon {
  font-size: 10px;
  color: #64748b;
  width: 14px;
}

.project-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.project-status {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.project-status.active {
  background: #dcfce7;
  color: #16a34a;
}

.project-status.archived {
  background: #f1f5f9;
  color: #64748b;
}

.project-meta {
  display: flex;
  gap: 16px;
  flex: 1;
  padding: 0 24px;
}

.meta-item {
  font-size: 12px;
  color: #64748b;
}

.project-actions {
  display: flex;
  gap: 6px;
}

/* 展开详情 */
.project-detail {
  padding: 16px 20px;
  border-top: 1px solid #e2e8f0;
  background: white;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

.detail-header .detail-label {
  margin-bottom: 0;
}

.detail-content {
  font-size: 14px;
  color: #334155;
  line-height: 1.6;
}

/* 别名标签 */
.alias-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.alias-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #e2e8f0;
  color: #475569;
  border-radius: 4px;
  font-size: 13px;
}

.alias-tag.removable {
  padding-right: 6px;
}

.alias-remove {
  width: 18px;
  height: 18px;
  border: none;
  background: rgba(100, 116, 139, 0.2);
  color: #475569;
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 2px;
}

.alias-remove:hover {
  background: rgba(100, 116, 139, 0.3);
}

/* 别名列表编辑 */
.alias-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alias-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alias-edit-input {
  flex: 1;
  padding: 6px 10px !important;
  font-size: 13px !important;
}

.alias-action-btn {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.alias-action-btn.edit {
  background: #e2e8f0;
  color: #475569;
}

.alias-action-btn.edit:hover {
  background: #cbd5e1;
}

.alias-action-btn.save {
  background: #dcfce7;
  color: #16a34a;
}

.alias-action-btn.save:hover {
  background: #bbf7d0;
}

.alias-action-btn.cancel {
  background: #f1f5f9;
  color: #64748b;
}

.alias-action-btn.cancel:hover {
  background: #e2e8f0;
}

.alias-action-btn.delete {
  background: #fee2e2;
  color: #ef4444;
}

.alias-action-btn.delete:hover {
  background: #fecaca;
  color: #dc2626;
}

/* 子项目 */
.sub-items-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sub-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.sub-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sub-item-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.sub-item-desc {
  font-size: 12px;
  color: #64748b;
}

.sub-item-actions {
  display: flex;
  gap: 4px;
}

.empty-sub-items {
  padding: 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* 操作按钮 */
.action-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f1f5f9;
  color: #64748b;
  white-space: nowrap;
}

.action-btn:hover {
  background: #e2e8f0;
  color: #475569;
}

.action-btn.edit {
  background: #e2e8f0;
  color: #475569;
}

.action-btn.edit:hover {
  background: #cbd5e1;
}

.action-btn.approve {
  background: #dcfce7;
  color: #16a34a;
}

.action-btn.approve:hover {
  background: #bbf7d0;
}

.action-btn.merge {
  background: #e2e8f0;
  color: #475569;
}

.action-btn.merge:hover {
  background: #cbd5e1;
}

.action-btn.reject,
.action-btn.delete {
  color: #ef4444;
}

.action-btn.reject:hover,
.action-btn.delete:hover {
  background: #fee2e2;
  color: #dc2626;
}

.action-btn-small {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  background: #f1f5f9;
  color: #64748b;
}

.action-btn-small:hover {
  background: #e2e8f0;
}

.action-btn-small.delete:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* 待审核列表 */
.pending-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pending-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fffbeb;
  border-radius: 8px;
  border: 1px solid #fde68a;
}

.pending-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pending-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.pending-meta {
  font-size: 12px;
  color: #64748b;
}

.pending-actions {
  display: flex;
  gap: 8px;
}

/* 黑名单 */
.rejected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rejected-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f1f5f9;
  border-radius: 6px;
}

.rejected-name {
  font-size: 13px;
  color: #64748b;
}

/* 系统管理部分 */
.system-section {
  padding: 4px 0;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.section-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}

.analysis-form {
  margin-top: 12px;
}

.form-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.form-input-small {
  width: 80px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  text-align: center;
  background: white;
  color: #0f172a;
}

.form-input-small:focus {
  outline: none;
  border-color: #7aaed8;
  box-shadow: 0 0 0 3px rgba(99, 176, 221, 0.15);
}

.form-text {
  font-size: 14px;
  color: #64748b;
}

/* 设置项样式 */
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.setting-desc {
  font-size: 12px;
  color: #64748b;
}

/* 开关样式 */
.toggle-switch {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-switch input {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background: #e2e8f0;
  border-radius: 12px;
  transition: background 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.toggle-switch input:checked + .toggle-slider {
  background: #7aaed8;
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(20px);
}

/* 加载和空状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #64748b;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #7aaed8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #64748b;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.6;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
  animation: modalIn 0.2s ease;
}

.modal-large {
  max-width: 560px;
}

.modal-small {
  max-width: 420px;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 18px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: #e2e8f0;
  color: #334155;
}

.modal-body {
  padding: 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-text {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  background: #f8fafc;
  border-radius: 0 0 12px 12px;
}

/* 表单 */
.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 8px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: white;
  color: #0f172a;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #7aaed8;
  box-shadow: 0 0 0 3px rgba(99, 176, 221, 0.15);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.alias-input-row {
  display: flex;
  gap: 8px;
}

.alias-input-row .form-input {
  flex: 1;
}

/* 类别管理 */
.category-add-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.category-add-row .form-input {
  flex: 1;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 6px;
}

.category-name {
  font-size: 14px;
  color: #334155;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 16px;
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .page-title {
    font-size: 1.25rem;
    text-align: center;
  }

  .header-actions {
    flex-wrap: wrap;
    justify-content: center;
  }

  .project-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .project-meta {
    padding: 0;
    flex-direction: column;
    gap: 4px;
  }

  .project-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .pending-item {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .pending-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
