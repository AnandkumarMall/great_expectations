import React from 'react'
import DocSidebarItems from '@theme-original/DocSidebarItems'
import { useNavbarMobileSidebar } from '@docusaurus/theme-common/internal'
const MOBILE_BREAKPOINT = 996

export default function DocSidebarItemsWrapper (props) {
  const mobileSidebar = useNavbarMobileSidebar()

  const handleMobileDocSidebarItemClick = (item) => {
    if (typeof window === 'undefined' || window.innerWidth > MOBILE_BREAKPOINT) return
    if (!props.onItemClick) return
    if (item.type === 'link') {
      mobileSidebar.toggle()
    }
  }
  return (
    <DocSidebarItems {...props} onItemClick={handleMobileDocSidebarItemClick} />
  )
}
