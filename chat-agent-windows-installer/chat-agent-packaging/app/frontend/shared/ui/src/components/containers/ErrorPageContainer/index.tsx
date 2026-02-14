import { FC } from 'react';

import {
  StyledErrorPageContainer,
  StyledErrorPageWrapper,
} from '@shared/ui/components/containers/ErrorPageContainer/ErrorPageContainer.styled';
import CustomFooter from '@shared/ui/components/organisms/Footers/CustomFooter';

import { ErrorPageContainerProps } from '@shared/ui/components/containers/ErrorPageContainer/ErrorPageContainer.props';

const ErrorPageContainer: FC<ErrorPageContainerProps> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <StyledErrorPageContainer
      className={`error-page-container ${className}`}
      {...props}
    >
      <StyledErrorPageWrapper>{children}</StyledErrorPageWrapper>
      <CustomFooter />
    </StyledErrorPageContainer>
  );
};

export default ErrorPageContainer;
