import { FC } from 'react';
import { Layout } from 'antd';

import {
  StyledAppsContainer,
  StyledAppsContainerContent,
} from '@shared/ui/components/containers/AppsContainer/AppsContainer.styled';

import { AppsContainerProps } from '@shared/ui/components/containers/AppsContainer/AppsContainer.props';
import AppsSidebar from '@shared/ui/components/organisms/Sidebars/AppsSidebar';

const AppsContainer: FC<AppsContainerProps> = ({
  className = '',
  children,
  menuItems = [],
  ...props
}) => {
  return (
    <StyledAppsContainer
      hasSider
      className={`apps-container ${className}`}
      {...props}
    >
      <AppsSidebar menuItems={menuItems} />
      <Layout>
        <StyledAppsContainerContent> {children}</StyledAppsContainerContent>
      </Layout>
    </StyledAppsContainer>
  );
};

export default AppsContainer;
