import { FC } from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

import { StyledAppsGroupContainer } from '@/components/organisms/Apps/AppsGroup/AppsGroup.styled';
import AppsItem from '@/components/molecules/Apps/AppsItem';

import { AppsGroupProps } from '@/components/organisms/Apps/AppsGroup/AppsGroup.props';

const AppsGroup: FC<AppsGroupProps> = ({
  title = '',
  items = [],
  className = '',
  ...props
}) => {
  return (
    <div className={`apps-group ${className}`} {...props}>
      <Title level={4}>{title}</Title>
      <StyledAppsGroupContainer>
        {items.map((item) => (
          <AppsItem key={item.name} {...item} />
        ))}
      </StyledAppsGroupContainer>
    </div>
  );
};

export default AppsGroup;
