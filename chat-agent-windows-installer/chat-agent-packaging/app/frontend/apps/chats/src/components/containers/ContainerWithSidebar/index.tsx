import { FC } from 'react';
import { Layout } from 'antd';

import CustomHeader from '../../organisms/Headers/CustomHeader';
import {
  StyledContainerWithSidebar,
  StyledContainerWithSidebarContent,
} from '@/components/containers/ContainerWithSidebar/ContainerWithSidebar.styled';
import CustomFooter from '@shared/ui/components/organisms/Footers/CustomFooter';
import CustomSidebar from '../../organisms/Sidebars/CustomSidebar';

import { ContainerWithSidebarProps } from '@/components/containers/ContainerWithSidebar/ContainerWithSidebar.props';

const ContainerWithSidebar: FC<ContainerWithSidebarProps> = ({
  showChats = false,
  children,
}) => {
  return (
    <StyledContainerWithSidebar hasSider>
      <CustomSidebar showChats={showChats} />
      <Layout>
        <CustomHeader showChats={showChats} />
        <StyledContainerWithSidebarContent>
          {children}
        </StyledContainerWithSidebarContent>
        <CustomFooter />
      </Layout>
    </StyledContainerWithSidebar>
  );
};

export default ContainerWithSidebar;
